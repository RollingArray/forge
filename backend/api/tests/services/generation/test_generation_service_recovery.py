import hashlib
from pathlib import Path
import tempfile
from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.constants.generation import (
    DEFAULT_GENERATION_CHUNK_SIZE,
    GENERATION_ALGORITHM_VERSION,
)
from app.models.generation_persistence import (
    GenerationArtifactEvidence,
    GenerationFinalizationStatus,
)
from app.models.generation_model import (
    GenerationEntityProgress,
    GenerationJobRecord,
    GenerationJobResponse,
    GenerationJobStatus,
    GenerationLifecyclePhase,
    GenerationPreparationPhase,
    GenerationResumeIntent,
)
from app.repositories.file_lock import FileLockTimeout
import app.services.generation_service as generation_service_module
from app.services.generation_checkpoint_store import GenerationCheckpointStore
from app.services.generation_job_control_store import (
    GenerationJobControlRequest,
    GenerationJobControlStore,
)
from app.services.generation_job_store import GenerationJobStore
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

    temporary_directory = tempfile.TemporaryDirectory(
        prefix="forge-recovery-test-"
    )
    service._test_temporary_directory = temporary_directory
    service._job_store._job_path.return_value = (
        Path(temporary_directory.name) / "job.json"
    )

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


@pytest.mark.parametrize(
    (
        "target_rows",
        "committed_rows",
        "finalization_status",
        "expected_unfinished",
    ),
    [
        (10, 5, GenerationFinalizationStatus.PENDING, True),
        (10, 10, GenerationFinalizationStatus.PENDING, True),
        (10, 10, GenerationFinalizationStatus.IN_PROGRESS, True),
        (10, 10, GenerationFinalizationStatus.COMMITTED, False),
        (0, 0, GenerationFinalizationStatus.PENDING, True),
    ],
)
def test_checkpoint_unfinished_work_eligibility(
    target_rows,
    committed_rows,
    finalization_status,
    expected_unfinished,
):
    service, _ = build_service()
    checkpoint = make_valid_recovery_checkpoint()
    entity_checkpoint = checkpoint.entities["ORGANIZATION"]
    entity_checkpoint.target_rows = target_rows
    entity_checkpoint.committed_rows = committed_rows
    entity_checkpoint.finalization.status = finalization_status

    assert (
        service._checkpoint_has_unfinished_work(checkpoint)
        is expected_unfinished
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


@pytest.mark.parametrize(
    "source_status",
    [
        GenerationJobStatus.INTERRUPTED,
        GenerationJobStatus.FAILED,
        GenerationJobStatus.PARTIALLY_COMPLETED,
        GenerationJobStatus.PAUSED,
        GenerationJobStatus.CANCELLED,
    ],
)
def test_startup_reconciles_already_superseded_resume_without_worker(source_status):
    service, _ = build_service()
    job = make_job(source_status)

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


@pytest.mark.parametrize(
    "source_status",
    [
        GenerationJobStatus.INTERRUPTED,
        GenerationJobStatus.FAILED,
        GenerationJobStatus.PARTIALLY_COMPLETED,
        GenerationJobStatus.PAUSED,
        GenerationJobStatus.CANCELLED,
    ],
)
def test_startup_reconciles_resume_intent_before_checkpoint_supersession(source_status):
    service, _ = build_service()
    job = make_job(source_status)

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




@pytest.mark.parametrize(
    "source_status",
    [
        GenerationJobStatus.INTERRUPTED,
        GenerationJobStatus.FAILED,
        GenerationJobStatus.PARTIALLY_COMPLETED,
        GenerationJobStatus.PAUSED,
        GenerationJobStatus.CANCELLED,
    ],
)
def test_interrupted_resume_preserves_real_committed_checkpoint_evidence(
    tmp_path,
    monkeypatch,
    source_status,
):
    """Resume a partially committed job using real file-backed stores."""

    chunk_size = 5
    old_attempt_id = "recovery-attempt-001"
    new_attempt_id = "resume-attempt-real-store-002"

    specification = {
        "name": "Test Model",
        "generation": {"seed": 42},
        "entities": [],
    }

    job_store = GenerationJobStore()
    job_store._root = tmp_path

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path

    service = GenerationService(
        specification_service=FakeSpecificationService(specification),
        specification_validation_service=FakeValidationService(),
        checkpoint_store=checkpoint_store,
        generation_log_store=MagicMock(),
    )
    service._job_store = job_store
    service._generation_planner = MagicMock()
    service._generation_planner.build.return_value = SimpleNamespace(
        entities=[
            SimpleNamespace(
                entity_name="ORGANIZATION",
                target_rows=10,
            )
        ]
    )

    job = make_job(
        source_status,
        chunk_size=chunk_size,
    )
    job.attempt_id = old_attempt_id
    job.error = "Previous execution was interrupted."

    checkpoint_store.initialize(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        specification=specification,
        seed=42,
        chunk_size=chunk_size,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=old_attempt_id,
        entity_targets={"ORGANIZATION": 10},
    )

    artifact_bytes = (
        b"ID,NAME\n"
        b"1,Organization One\n"
        b"2,Organization Two\n"
        b"3,Organization Three\n"
        b"4,Organization Four\n"
        b"5,Organization Five\n"
    )
    artifact_relative_path = "generated/organization/chunk-1.csv"
    artifact_path = (
        checkpoint_store._job_directory(DATA_MODEL_ID, JOB_ID)
        / artifact_relative_path
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(artifact_bytes)

    artifact = GenerationArtifactEvidence(
        path=artifact_relative_path,
        size_bytes=len(artifact_bytes),
        sha256=hashlib.sha256(artifact_bytes).hexdigest(),
    )

    checkpoint_store.commit_chunk(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        attempt_id=old_attempt_id,
        entity_name="ORGANIZATION",
        chunk_number=1,
        row_start=0,
        row_count=chunk_size,
        artifact=artifact,
    )

    before_resume = checkpoint_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )
    assert before_resume is not None
    assert before_resume.attempt_id == old_attempt_id
    assert before_resume.entities["ORGANIZATION"].committed_rows == 5
    assert [
        chunk.chunk_number
        for chunk in before_resume.entities["ORGANIZATION"].chunks
    ] == [1]

    original_chunk_evidence = (
        before_resume.entities["ORGANIZATION"].chunks[0]
    )
    original_artifact_bytes = artifact_path.read_bytes()
    original_artifact_hash = hashlib.sha256(
        original_artifact_bytes
    ).hexdigest()

    job_store.save(job)

    monkeypatch.setattr(
        generation_service_module,
        "generation_execution_lease",
        lambda *args, **kwargs: nullcontext(),
    )
    monkeypatch.setattr(
        generation_service_module,
        "uuid4",
        lambda: SimpleNamespace(hex=new_attempt_id),
    )

    resumed = service.start_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert resumed is not None
    assert resumed.status == GenerationJobStatus.PREPARING
    assert resumed.attempt_id == new_attempt_id
    assert resumed.attempt_id != old_attempt_id
    assert resumed.resume_intent is None
    assert resumed.preparation_phase == (
        GenerationPreparationPhase.CHECKPOINT_READY
    )
    assert resumed.error is None

    persisted_job = job_store.get(DATA_MODEL_ID, JOB_ID)
    assert persisted_job is not None
    assert persisted_job.status == GenerationJobStatus.PREPARING
    assert persisted_job.attempt_id == new_attempt_id
    assert persisted_job.resume_intent is None
    assert persisted_job.preparation_phase == (
        GenerationPreparationPhase.CHECKPOINT_READY
    )

    persisted_checkpoint = checkpoint_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )
    assert persisted_checkpoint is not None
    assert persisted_checkpoint.attempt_id == new_attempt_id

    entity_checkpoint = persisted_checkpoint.entities["ORGANIZATION"]
    assert entity_checkpoint.committed_rows == 5
    assert [chunk.chunk_number for chunk in entity_checkpoint.chunks] == [1]
    assert entity_checkpoint.chunks[0] == original_chunk_evidence

    # The committed artifact remains byte-for-byte identical and verifiable.
    assert artifact_path.read_bytes() == original_artifact_bytes
    assert hashlib.sha256(artifact_path.read_bytes()).hexdigest() == (
        original_artifact_hash
    )
    checkpoint_store.verify_artifact(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        artifact=entity_checkpoint.chunks[0].artifact,
    )

    # The job projection is rebuilt from durable checkpoint evidence.
    assert persisted_job.total_generated_rows == 5
    assert persisted_job.progress == 0.5
    assert persisted_job.entities[0].generated_rows == 5
    assert persisted_job.entities[0].completed_chunks == 1
    assert persisted_job.entities[0].total_chunks == 2

    # Chunk 2 remains outstanding for the resumed executor.
    assert [
        chunk.chunk_number
        for chunk in entity_checkpoint.chunks
    ] == [1]

    assert (DATA_MODEL_ID, JOB_ID) in service._active_workers


def test_fully_finalized_checkpoint_rejects_retry_without_mutation(
    tmp_path,
    monkeypatch,
):
    """A fully finalized checkpoint must not be regenerated."""

    old_attempt_id = "finalized-attempt-001"
    specification = {
        "name": "Test Model",
        "generation": {"seed": 42},
        "entities": [],
    }

    job_store = GenerationJobStore()
    job_store._root = tmp_path

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path

    service = GenerationService(
        specification_service=FakeSpecificationService(specification),
        specification_validation_service=FakeValidationService(),
        checkpoint_store=checkpoint_store,
        generation_log_store=MagicMock(),
    )
    service._job_store = job_store
    service._generation_planner = MagicMock()
    service._generation_planner.build.return_value = SimpleNamespace(
        entities=[
            SimpleNamespace(
                entity_name="ORGANIZATION",
                target_rows=10,
            )
        ]
    )

    job = make_job(
        GenerationJobStatus.PARTIALLY_COMPLETED,
        chunk_size=5,
    )
    job.attempt_id = old_attempt_id
    job.error = "A post-generation validation step failed."

    checkpoint_store.initialize(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        specification=specification,
        seed=42,
        chunk_size=5,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=old_attempt_id,
        entity_targets={"ORGANIZATION": 10},
    )

    # Commit all target rows as two valid five-row chunks.
    job_directory = checkpoint_store._job_directory(
        DATA_MODEL_ID,
        JOB_ID,
    )

    chunk_artifacts = [
        (
            1,
            0,
            b"ID,NAME\\n"
            b"1,Organization One\\n"
            b"2,Organization Two\\n"
            b"3,Organization Three\\n"
            b"4,Organization Four\\n"
            b"5,Organization Five\\n",
        ),
        (
            2,
            5,
            b"ID,NAME\\n"
            b"6,Organization Six\\n"
            b"7,Organization Seven\\n"
            b"8,Organization Eight\\n"
            b"9,Organization Nine\\n"
            b"10,Organization Ten\\n",
        ),
    ]

    committed_chunk_evidence = []
    committed_chunk_paths = []

    for chunk_number, row_start, chunk_bytes in chunk_artifacts:
        relative_path = (
            f"generated/organization/chunk-{chunk_number}.csv"
        )
        artifact_path = job_directory / relative_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(chunk_bytes)

        evidence = GenerationArtifactEvidence(
            path=relative_path,
            size_bytes=len(chunk_bytes),
            sha256=hashlib.sha256(chunk_bytes).hexdigest(),
        )

        checkpoint_store.commit_chunk(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            attempt_id=old_attempt_id,
            entity_name="ORGANIZATION",
            chunk_number=chunk_number,
            row_start=row_start,
            row_count=5,
            artifact=evidence,
        )

        committed_chunk_evidence.append(evidence)
        committed_chunk_paths.append((artifact_path, chunk_bytes))

    checkpoint_store.begin_finalization(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        attempt_id=old_attempt_id,
        entity_name="ORGANIZATION",
    )

    # Commit the consolidated output through the real finalization API.
    output_bytes = (
        b"ID,NAME\n"
        b"1,Organization One\n"
        b"2,Organization Two\n"
        b"3,Organization Three\n"
        b"4,Organization Four\n"
        b"5,Organization Five\n"
        b"6,Organization Six\n"
        b"7,Organization Seven\n"
        b"8,Organization Eight\n"
        b"9,Organization Nine\n"
        b"10,Organization Ten\n"
    )
    output_relative_path = "generated/organization/final.csv"
    output_path = job_directory / output_relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output_bytes)

    output_evidence = GenerationArtifactEvidence(
        path=output_relative_path,
        size_bytes=len(output_bytes),
        sha256=hashlib.sha256(output_bytes).hexdigest(),
    )

    checkpoint_store.commit_finalization(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        attempt_id=old_attempt_id,
        entity_name="ORGANIZATION",
        output=output_evidence,
    )

    before_checkpoint = checkpoint_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )
    assert before_checkpoint is not None
    entity = before_checkpoint.entities["ORGANIZATION"]
    assert entity.committed_rows == 10
    assert entity.finalization.status == GenerationFinalizationStatus.COMMITTED
    assert entity.finalization.output == output_evidence

    job_store.save(job)

    before_job = job_store.get(DATA_MODEL_ID, JOB_ID)
    assert before_job is not None

    monkeypatch.setattr(
        generation_service_module,
        "generation_execution_lease",
        lambda *args, **kwargs: nullcontext(),
    )

    with pytest.raises(
        ValueError,
        match="no unfinished work to resume",
    ):
        service.start_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    # The rejected retry must not mutate the persisted job.
    after_job = job_store.get(DATA_MODEL_ID, JOB_ID)
    assert after_job is not None
    assert after_job.status == before_job.status
    assert after_job.attempt_id == old_attempt_id
    assert after_job.resume_intent is None
    assert after_job.error == before_job.error

    # The checkpoint manifest and both committed artifacts remain intact.
    after_checkpoint = checkpoint_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )
    assert after_checkpoint == before_checkpoint
    assert output_path.read_bytes() == output_bytes

    for artifact_path, expected_bytes in committed_chunk_paths:
        assert artifact_path.read_bytes() == expected_bytes

    for evidence in committed_chunk_evidence:
        checkpoint_store.verify_artifact(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            artifact=evidence,
        )

    checkpoint_store.verify_artifact(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        artifact=output_evidence,
    )

    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers



def make_finalized_recovery_checkpoint(
    attempt_id="recovery-attempt-001",
    chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
):
    checkpoint = make_valid_recovery_checkpoint(
        attempt_id=attempt_id,
        chunk_size=chunk_size,
    )
    entity = checkpoint.entities["ORGANIZATION"]
    entity.committed_rows = entity.target_rows
    entity.chunks = [
        SimpleNamespace(
            chunk_number=1,
            row_count=10,
            artifact=object(),
        )
    ]
    entity.finalization.status = GenerationFinalizationStatus.COMMITTED
    entity.finalization.output = object()
    return checkpoint


def test_finalizing_resume_reuses_existing_attempt_without_supersession():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)
    job.lifecycle_phase = GenerationLifecyclePhase.FINALIZING

    original_attempt_id = job.attempt_id
    manifest = make_finalized_recovery_checkpoint(original_attempt_id)

    configure_recovery_validation(service, manifest)
    service._checkpoint_store.get.return_value = manifest
    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job

    resumed = service.start_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert resumed is job
    assert job.status == GenerationJobStatus.PREPARING
    assert job.lifecycle_phase == GenerationLifecyclePhase.FINALIZING
    assert job.attempt_id == original_attempt_id
    assert job.resume_intent is None
    assert job.preparation_phase == GenerationPreparationPhase.CHECKPOINT_READY
    assert job.total_generated_rows == 10
    assert job.progress == 1.0

    service._checkpoint_store.supersede_attempt.assert_not_called()
    service._job_store.save.assert_called_once_with(job)
    assert (DATA_MODEL_ID, JOB_ID) in service._active_workers


def test_finalizing_resume_rejects_incomplete_checkpoint():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)
    job.lifecycle_phase = GenerationLifecyclePhase.FINALIZING

    manifest = make_valid_recovery_checkpoint(
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,)
    configure_recovery_validation(service, manifest)
    service._checkpoint_store.get.return_value = manifest
    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job

    with pytest.raises(ValueError, match="FINALIZING"):
        service.start_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    assert job.status == GenerationJobStatus.INTERRUPTED
    assert job.attempt_id == "recovery-attempt-001"
    assert job.resume_intent is None
    service._checkpoint_store.supersede_attempt.assert_not_called()
    service._job_store.save.assert_not_called()
    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers


def test_startup_recovery_preserves_finalizing_phase():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.RUNNING)
    job.lifecycle_phase = GenerationLifecyclePhase.FINALIZING

    manifest = make_finalized_recovery_checkpoint(job.attempt_id)
    service._jobs[job.job_id] = job
    service._job_store.get.return_value = job
    service._job_store.list_recoverable.return_value = [job]
    service._reconcile_recovery_checkpoint = MagicMock(
        return_value=manifest
    )

    recovered = service.recover_interrupted_jobs()

    assert recovered == 1
    assert job.status == GenerationJobStatus.INTERRUPTED
    assert job.lifecycle_phase == GenerationLifecyclePhase.FINALIZING
    assert job.attempt_id == "recovery-attempt-001"
    service._job_store.save.assert_called_once_with(job)
    service._checkpoint_store.supersede_attempt.assert_not_called()

@pytest.mark.parametrize(
    ("control_request", "expected_status"),
    [
        (
            GenerationJobControlRequest.PAUSE,
            GenerationJobStatus.PAUSED,
        ),
        (
            GenerationJobControlRequest.CANCEL,
            GenerationJobStatus.CANCELLED,
        ),
    ],
)
def test_startup_recovery_consumes_pending_generation_control(
    tmp_path,
    control_request,
    expected_status,
):
    service, _ = build_service()

    job_store = GenerationJobStore()
    job_store._root = tmp_path
    control_store = GenerationJobControlStore()
    control_store._root = tmp_path

    service._job_store = job_store
    service._control_store = control_store

    job = make_job(GenerationJobStatus.RUNNING)
    job.lifecycle_phase = GenerationLifecyclePhase.GENERATING
    job_store.save(job)

    control_store.request(DATA_MODEL_ID, JOB_ID, control_request)

    # Verify that the request remains durable while the job outcome is saved.
    original_save = job_store.save

    def verify_request_precedes_job_save(record):
        assert (
            control_store.get_request(DATA_MODEL_ID, JOB_ID)
            == control_request
        )
        original_save(record)

    job_store.save = verify_request_precedes_job_save

    service._jobs[job.job_id] = job
    service._reconcile_recovery_checkpoint = MagicMock(
        return_value=make_valid_recovery_checkpoint(
            chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        )
    )

    recovered = service.recover_interrupted_jobs()

    persisted_job = job_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert recovered == 1
    assert persisted_job is not None
    assert persisted_job.status == expected_status
    assert (
        persisted_job.lifecycle_phase
        == GenerationLifecyclePhase.GENERATING
    )
    assert control_store.get_request(DATA_MODEL_ID, JOB_ID) is None



def _build_file_backed_control_recovery(tmp_path, control_request):
    service, _ = build_service()

    job_store = GenerationJobStore()
    job_store._root = tmp_path

    control_store = GenerationJobControlStore()
    control_store._root = tmp_path

    service._job_store = job_store
    service._control_store = control_store

    job = make_job(GenerationJobStatus.RUNNING)
    job.lifecycle_phase = GenerationLifecyclePhase.GENERATING
    job_store.save(job)

    control_store.request(DATA_MODEL_ID, JOB_ID, control_request)

    service._jobs[job.job_id] = job
    service._reconcile_recovery_checkpoint = MagicMock(
        return_value=make_valid_recovery_checkpoint(
            chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        )
    )

    return service, job_store, control_store, job


def test_recovery_preserves_newer_cancel_request_during_conditional_clear(
    tmp_path,
):
    service, job_store, control_store, job = (
        _build_file_backed_control_recovery(
            tmp_path,
            GenerationJobControlRequest.PAUSE,
        )
    )

    original_clear = control_store.clear_request_if_matches
    clear_calls = []

    def upgrade_pause_before_clear(data_model_id, job_id, expected):
        clear_calls.append(expected)

        if len(clear_calls) == 1:
            assert expected == GenerationJobControlRequest.PAUSE
            control_store.request(
                data_model_id,
                job_id,
                GenerationJobControlRequest.CANCEL,
            )

        return original_clear(data_model_id, job_id, expected)

    control_store.clear_request_if_matches = upgrade_pause_before_clear

    recovered = service.recover_interrupted_jobs()

    persisted_job = job_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert recovered == 1
    assert persisted_job is not None
    assert persisted_job.status == GenerationJobStatus.CANCELLED
    assert persisted_job.lifecycle_phase == GenerationLifecyclePhase.GENERATING
    assert clear_calls == [
        GenerationJobControlRequest.PAUSE,
        GenerationJobControlRequest.CANCEL,
    ]
    assert control_store.get_request(DATA_MODEL_ID, JOB_ID) is None


def test_recovery_keeps_control_request_when_status_persistence_fails(
    tmp_path,
):
    service, job_store, control_store, job = (
        _build_file_backed_control_recovery(
            tmp_path,
            GenerationJobControlRequest.PAUSE,
        )
    )

    original_save = job_store.save

    def fail_before_persisting_requested_status(record):
        if record.status == GenerationJobStatus.PAUSED:
            raise RuntimeError("Simulated recovery persistence failure")
        original_save(record)

    job_store.save = fail_before_persisting_requested_status

    recovered = service.recover_interrupted_jobs()

    persisted_job = job_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert recovered == 0
    assert persisted_job is not None
    assert persisted_job.status == GenerationJobStatus.RUNNING
    assert persisted_job.lifecycle_phase == GenerationLifecyclePhase.GENERATING
    assert control_store.get_request(DATA_MODEL_ID, JOB_ID) == (
        GenerationJobControlRequest.PAUSE
    )
    assert job.status == GenerationJobStatus.RUNNING


def test_recovery_reconciles_status_when_save_raises_after_durable_write(
    tmp_path,
):
    service, job_store, control_store, job = (
        _build_file_backed_control_recovery(
            tmp_path,
            GenerationJobControlRequest.CANCEL,
        )
    )

    original_save = job_store.save

    def persist_then_report_failure(record):
        original_save(record)

        if record.status == GenerationJobStatus.CANCELLED:
            raise RuntimeError(
                "Simulated failure after durable job replacement"
            )

    job_store.save = persist_then_report_failure

    recovered = service.recover_interrupted_jobs()

    persisted_job = job_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert recovered == 1
    assert persisted_job is not None
    assert persisted_job.status == GenerationJobStatus.CANCELLED
    assert persisted_job.lifecycle_phase == GenerationLifecyclePhase.GENERATING
    assert control_store.get_request(DATA_MODEL_ID, JOB_ID) is None
