from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.constants.generation import DEFAULT_GENERATION_CHUNK_SIZE
from app.models.generation_model import (
    GenerationEntityProgress,
    GenerationJobRecord,
    GenerationJobResponse,
    GenerationJobStatus,
    GenerationPreparationPhase,
    GenerationResumeIntent,
)
from app.repositories.file_lock import FileLockTimeout
import app.services.generation_service as generation_service_module
from app.services.generation_service import GenerationService


DATA_MODEL_ID = "MODEL-TEST"
JOB_ID = "JOB-TEST"

SPECIFICATION = {
    "name": "Test Model",
    "generation": {"seed": 42},
    "entities": [],
}


class FakeSpecificationService:
    def __init__(self, specification=SPECIFICATION):
        self.specification = specification

    def get_specification(self, *, data_model_id):
        return self.specification


class FakeValidationService:
    def __init__(self):
        self.calls = 0

    def validate(self, specification):
        self.calls += 1
        return {
            "can_continue": True,
            "errors": 0,
            "warnings": 0,
            "findings": [],
        }


def build_service(specification=SPECIFICATION):
    validation_service = FakeValidationService()

    service = GenerationService(
        specification_service=FakeSpecificationService(specification),
        specification_validation_service=validation_service,
        checkpoint_store=MagicMock(),
        generation_log_store=MagicMock(),
    )
    service._job_store = MagicMock()

    return service, validation_service


def make_job(status, *, chunk_size: int = DEFAULT_GENERATION_CHUNK_SIZE):
    response = GenerationJobResponse(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        status=status,
        created_at=datetime.now(timezone.utc),
        total_target_rows=10,
        total_generated_rows=0,
        progress=0.0,
        entities=[
            GenerationEntityProgress(
                entity_name="ORGANIZATION",
                target_rows=10,
                chunk_size=chunk_size,
            )
        ],
    )
    job_data = response.model_dump(exclude={"throughput_rows_per_second"})
    job_data["attempt_id"] = "recovery-attempt-001"
    return GenerationJobRecord.model_validate(job_data)


def make_valid_recovery_checkpoint(
    chunk_size=250,
    attempt_id="recovery-attempt-001",
):
    return SimpleNamespace(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        attempt_id=attempt_id,
        chunk_size=chunk_size,
        entities={
            "ORGANIZATION": SimpleNamespace(
                target_rows=10,
                committed_rows=0,
                chunks=[],
                finalization=SimpleNamespace(
                    status="PENDING",
                    output=None,
                ),
            )
        },
    )


def configure_recovery_validation(service, checkpoint):
    service._checkpoint_store.get.return_value = checkpoint
    service._generation_planner = MagicMock()
    service._generation_planner.build.return_value = SimpleNamespace(
        entities=[
            SimpleNamespace(
                entity_name="ORGANIZATION",
                target_rows=10,
            )
        ]
    )


def test_recovery_validation_accepts_250_row_chunk_size():
    service, _ = build_service()
    job = make_job(
        GenerationJobStatus.INTERRUPTED,
        chunk_size=250,
    )
    checkpoint = make_valid_recovery_checkpoint(chunk_size=250)
    configure_recovery_validation(service, checkpoint)

    validated = service._validate_recovery_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    assert validated == checkpoint
    service._checkpoint_store.validate_identity.assert_called_once()
    assert (
        service._checkpoint_store.validate_identity.call_args.kwargs[
            "chunk_size"
        ]
        == 250
    )


def test_recovery_validation_rejects_job_checkpoint_chunk_size_mismatch():
    service, _ = build_service()
    job = make_job(
        GenerationJobStatus.INTERRUPTED,
        chunk_size=50,
    )
    checkpoint = make_valid_recovery_checkpoint(chunk_size=250)
    configure_recovery_validation(service, checkpoint)

    with pytest.raises(
        ValueError,
        match="same positive chunk size",
    ):
        service._validate_recovery_checkpoint(
            data_model_id=DATA_MODEL_ID,
            job=job,
            specification=SPECIFICATION,
        )

    service._checkpoint_store.validate_identity.assert_called_once()
    assert (
        service._checkpoint_store.validate_identity.call_args.kwargs        ["chunk_size"]
        == 250
    )


def test_startup_recovery_marks_running_job_interrupted():
    service, validator = build_service()
    job = make_job(GenerationJobStatus.RUNNING)

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.list_recoverable.return_value = [job]
    service._reconcile_recovery_checkpoint = MagicMock(return_value={})

    recovered = service.recover_interrupted_jobs()

    assert recovered == 1
    assert job.status == GenerationJobStatus.INTERRUPTED
    assert job.error is None
    assert validator.calls == 1
    service._reconcile_recovery_checkpoint.assert_called_once()
    service._job_store.save.assert_called_once_with(job)
    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers


def test_failed_startup_recovery_persistence_restores_state_for_retry():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.RUNNING)

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.list_recoverable.return_value = [job]
    service._reconcile_recovery_checkpoint = MagicMock(return_value={})
    service._job_store.save.side_effect = OSError(
        "Persistence unavailable"
    )

    first_attempt = service.recover_interrupted_jobs()

    assert first_attempt == 0
    assert job.status == GenerationJobStatus.RUNNING

    service._job_store.save.side_effect = None

    second_attempt = service.recover_interrupted_jobs()

    assert second_attempt == 1
    assert job.status == GenerationJobStatus.INTERRUPTED
    assert service._job_store.save.call_count == 2


def test_startup_recovery_is_idempotent_for_already_recovered_job():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.RUNNING)

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.list_recoverable.return_value = [job]
    service._reconcile_recovery_checkpoint = MagicMock(return_value={})

    assert service.recover_interrupted_jobs() == 1
    assert job.status == GenerationJobStatus.INTERRUPTED

    # The store's result is deliberately unchanged. The cached job state
    # must prevent the same job from being recovered a second time.
    assert service.recover_interrupted_jobs() == 0

    service._reconcile_recovery_checkpoint.assert_called_once()
    service._job_store.save.assert_called_once_with(job)


def test_startup_recovery_skips_job_when_specification_is_missing():
    service, validator = build_service(specification=None)
    job = make_job(GenerationJobStatus.RUNNING)

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.list_recoverable.return_value = [job]
    service._reconcile_recovery_checkpoint = MagicMock()

    recovered = service.recover_interrupted_jobs()

    assert recovered == 0
    assert job.status == GenerationJobStatus.RUNNING
    assert validator.calls == 0
    service._reconcile_recovery_checkpoint.assert_not_called()
    service._job_store.save.assert_not_called()


def test_startup_recovery_skips_job_when_checkpoint_reconciliation_fails():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.RUNNING)

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.list_recoverable.return_value = [job]
    service._reconcile_recovery_checkpoint = MagicMock(
        side_effect=ValueError("Checkpoint is missing.")
    )

    recovered = service.recover_interrupted_jobs()

    assert recovered == 0
    assert job.status == GenerationJobStatus.RUNNING
    service._reconcile_recovery_checkpoint.assert_called_once()
    service._job_store.save.assert_not_called()


def test_interrupted_job_resume_persists_intent_then_preparing(monkeypatch):
    service, validator = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)

    old_manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        attempt_id=job.attempt_id,
    )
    new_attempt_id = "resume-attempt-002"
    monkeypatch.setattr(
        generation_service_module,
        "uuid4",
        lambda: SimpleNamespace(hex=new_attempt_id),
    )
    new_manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        attempt_id=new_attempt_id,
    )

    configure_recovery_validation(service, old_manifest)
    service._checkpoint_store.get.side_effect = [
        old_manifest,  # Initial validation before recording intent.
        old_manifest,  # Reconciliation reads the manifest.
        old_manifest,  # Validation before supersession.
        new_manifest,  # Validation after supersession.
    ]

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job

    resumed = service.start_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert resumed is job
    assert job.status == GenerationJobStatus.PREPARING
    assert job.attempt_id != "recovery-attempt-001"
    assert job.attempt_id == new_attempt_id
    assert job.preparation_phase == (
        GenerationPreparationPhase.CHECKPOINT_READY
    )
    assert job.resume_intent is None
    assert job.error is None
    assert validator.calls == 1

    # The first save persists the intent. The second completes the transition.
    assert service._job_store.save.call_count == 2

    service._checkpoint_store.supersede_attempt.assert_called_once_with(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        expected_attempt_id="recovery-attempt-001",
        new_attempt_id=new_attempt_id,
    )

    assert (DATA_MODEL_ID, JOB_ID) in service._active_workers


def test_resume_intent_save_failure_leaves_checkpoint_untouched():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)
    job.error = "Previous interruption detail"

    manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        attempt_id=job.attempt_id,
    )
    configure_recovery_validation(service, manifest)
    service._checkpoint_store.get.return_value = manifest

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.save.side_effect = OSError(
        "Persistence unavailable"
    )

    with pytest.raises(OSError, match="Persistence unavailable"):
        service.start_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    assert job.status == GenerationJobStatus.INTERRUPTED
    assert job.attempt_id == "recovery-attempt-001"
    assert job.resume_intent is None
    assert job.error == "Previous interruption detail"

    service._checkpoint_store.supersede_attempt.assert_not_called()
    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers


def test_failed_final_resume_save_preserves_durable_intent_for_recovery(
    monkeypatch,
):
    service, _ = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)
    job.error = "Previous interruption detail"

    old_manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        attempt_id=job.attempt_id,
    )
    new_attempt_id = "resume-attempt-after-save-failure"
    monkeypatch.setattr(
        generation_service_module,
        "uuid4",
        lambda: SimpleNamespace(hex=new_attempt_id),
    )
    new_manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        attempt_id=new_attempt_id,
    )

    configure_recovery_validation(service, old_manifest)
    service._checkpoint_store.get.side_effect = [
        old_manifest,
        old_manifest,
        old_manifest,
        new_manifest,
    ]

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job

    # Intent save succeeds. Final job transition save fails.
    service._job_store.save.side_effect = [
        None,
        OSError("Final job persistence unavailable"),
    ]

    with pytest.raises(
        OSError,
        match="Final job persistence unavailable",
    ):
        service.start_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    # The in-memory job returns to the durable intent state.
    assert job.status == GenerationJobStatus.INTERRUPTED
    assert job.attempt_id == "recovery-attempt-001"
    assert job.resume_intent is not None
    assert job.resume_intent.previous_attempt_id == "recovery-attempt-001"
    assert job.resume_intent.new_attempt_id == new_attempt_id
    assert job.error == "Previous interruption detail"

    # Checkpoint supersession happened, but the intent remains recoverable.
    service._checkpoint_store.supersede_attempt.assert_called_once()
    assert service._job_store.save.call_count == 2
    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers


def test_resume_rejects_checkpoint_attempt_outside_intent():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)
    job.resume_intent = GenerationResumeIntent(
        previous_attempt_id=job.attempt_id,
        new_attempt_id="resume-attempt-002",
    )

    unexpected_manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        attempt_id="unexpected-attempt",
    )
    service._checkpoint_store.get.return_value = unexpected_manifest

    with pytest.raises(
        ValueError,
        match="does not match either side",
    ):
        service._reconcile_resume_intent_under_lease(
            data_model_id=DATA_MODEL_ID,
            job=job,
            specification=SPECIFICATION,
            final_status=GenerationJobStatus.PREPARING,
        )

    service._checkpoint_store.supersede_attempt.assert_not_called()
    service._job_store.save.assert_not_called()


def test_startup_reconciles_already_superseded_resume_without_worker():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)

    new_attempt_id = "resume-attempt-002"
    job.resume_intent = GenerationResumeIntent(
        previous_attempt_id=job.attempt_id,
        new_attempt_id=new_attempt_id,
    )

    new_manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        attempt_id=new_attempt_id,
    )
    configure_recovery_validation(service, new_manifest)
    service._checkpoint_store.get.side_effect = [
        new_manifest,  # Reconciliation reads current checkpoint.
        new_manifest,  # Validate already-superseded checkpoint.
        new_manifest,  # Final validation.
    ]

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.list_recoverable.return_value = [job]

    recovered = service.recover_interrupted_jobs()

    assert recovered == 1
    assert job.status == GenerationJobStatus.INTERRUPTED
    assert job.attempt_id == new_attempt_id
    assert job.resume_intent is None
    assert job.preparation_phase == (
        GenerationPreparationPhase.CHECKPOINT_READY
    )

    service._checkpoint_store.supersede_attempt.assert_not_called()
    service._job_store.save.assert_called_once_with(job)
    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers


def test_startup_reconciles_resume_intent_before_checkpoint_supersession():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)

    old_attempt_id = job.attempt_id
    new_attempt_id = "resume-attempt-before-supersession"

    job.resume_intent = GenerationResumeIntent(
        previous_attempt_id=old_attempt_id,
        new_attempt_id=new_attempt_id,
    )

    old_manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        attempt_id=old_attempt_id,
    )
    new_manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        attempt_id=new_attempt_id,
    )

    configure_recovery_validation(service, old_manifest)
    service._checkpoint_store.get.side_effect = [
        old_manifest,  # Reconciliation reads the old checkpoint.
        old_manifest,  # Validate the old checkpoint before supersession.
        new_manifest,  # Validate the newly superseded checkpoint.
    ]

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.list_recoverable.return_value = [job]

    recovered = service.recover_interrupted_jobs()

    assert recovered == 1
    assert job.status == GenerationJobStatus.INTERRUPTED
    assert job.attempt_id == new_attempt_id
    assert job.resume_intent is None
    assert job.preparation_phase == (
        GenerationPreparationPhase.CHECKPOINT_READY
    )
    assert job.error is None

    service._checkpoint_store.supersede_attempt.assert_called_once_with(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        expected_attempt_id=old_attempt_id,
        new_attempt_id=new_attempt_id,
    )

    service._job_store.save.assert_called_once_with(job)
    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers


def test_startup_recovery_skips_job_when_execution_lease_is_busy(monkeypatch):
    service, _ = build_service()
    job = make_job(GenerationJobStatus.RUNNING)
    service._job_store.list_recoverable.return_value = [job]

    def busy_lease(*args, **kwargs):
        raise FileLockTimeout("Execution lease is already held.")

    monkeypatch.setattr(
        generation_service_module,
        "generation_execution_lease",
        busy_lease,
    )

    assert service.recover_interrupted_jobs() == 0
    assert job.status == GenerationJobStatus.RUNNING
    service._job_store.get.assert_not_called()
    service._job_store.save.assert_not_called()


def test_pending_preparation_initializes_missing_checkpoint():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.PREPARING)
    job.preparation_phase = GenerationPreparationPhase.CHECKPOINT_PENDING

    service._generation_planner = MagicMock()
    service._generation_planner.build.return_value = SimpleNamespace(
        entities=[
            SimpleNamespace(
                entity_name="ORGANIZATION",
                target_rows=10,
            )
        ]
    )

    manifest = object()
    service._checkpoint_store.get.return_value = None
    service._validate_recovery_checkpoint = MagicMock(
        return_value=manifest,
    )

    result = service._ensure_initial_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    assert result is manifest
    service._checkpoint_store.initialize.assert_called_once()
    initialize_args = service._checkpoint_store.initialize.call_args.kwargs
    assert initialize_args["attempt_id"] == job.attempt_id
    assert initialize_args["chunk_size"] == DEFAULT_GENERATION_CHUNK_SIZE
    assert initialize_args["entity_targets"] == {"ORGANIZATION": 10}
    service._validate_recovery_checkpoint.assert_called_once()
    assert (
        job.preparation_phase
        == GenerationPreparationPhase.CHECKPOINT_READY
    )
    service._job_store.save.assert_called_once_with(job)


def test_pending_preparation_reuses_existing_checkpoint():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.PREPARING)
    job.preparation_phase = GenerationPreparationPhase.CHECKPOINT_PENDING

    existing_manifest = object()
    service._checkpoint_store.get.return_value = existing_manifest
    service._validate_recovery_checkpoint = MagicMock(
        return_value=existing_manifest,
    )

    result = service._ensure_initial_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    assert result is existing_manifest
    service._checkpoint_store.initialize.assert_not_called()
    service._validate_recovery_checkpoint.assert_called_once()
    assert (
        job.preparation_phase
        == GenerationPreparationPhase.CHECKPOINT_READY
    )
    service._job_store.save.assert_called_once_with(job)


def test_ready_preparation_rejects_missing_checkpoint():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.PREPARING)
    job.preparation_phase = GenerationPreparationPhase.CHECKPOINT_READY
    service._checkpoint_store.get.return_value = None

    with pytest.raises(ValueError, match="CHECKPOINT_READY"):
        service._ensure_initial_checkpoint(
            data_model_id=DATA_MODEL_ID,
            job=job,
            specification=SPECIFICATION,
        )

    service._checkpoint_store.initialize.assert_not_called()
    service._job_store.save.assert_not_called()


def test_preparing_job_without_phase_is_not_reinitialized():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.PREPARING)
    job.preparation_phase = None
    service._checkpoint_store.get.return_value = None

    with pytest.raises(ValueError, match="preparation phase"):
        service._ensure_initial_checkpoint(
            data_model_id=DATA_MODEL_ID,
            job=job,
            specification=SPECIFICATION,
        )

    service._checkpoint_store.initialize.assert_not_called()


def test_startup_recovery_marks_preparing_job_interrupted():
    service, validator = build_service()
    job = make_job(GenerationJobStatus.PREPARING)
    job.preparation_phase = GenerationPreparationPhase.CHECKPOINT_READY

    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.list_recoverable.return_value = [job]
    service._ensure_initial_checkpoint = MagicMock()
    service._reconcile_recovery_checkpoint = MagicMock()

    recovered = service.recover_interrupted_jobs()

    assert recovered == 1
    assert job.status == GenerationJobStatus.INTERRUPTED
    assert validator.calls == 1
    service._ensure_initial_checkpoint.assert_called_once()
    service._reconcile_recovery_checkpoint.assert_called_once()
    service._job_store.save.assert_called_once_with(job)


