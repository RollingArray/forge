from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.generation_model import (
    GenerationEntityProgress,
    GenerationJobResponse,
    GenerationJobStatus,
)
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


def make_job(status):
    return GenerationJobResponse(
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
            )
        ],
    )


def test_startup_recovery_marks_running_job_interrupted():
    service, validator = build_service()
    job = make_job(GenerationJobStatus.RUNNING)

    service._jobs[job.job_id] = job
    service._job_store.list_running.return_value = [job]
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
    service._job_store.list_running.return_value = [job]
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
    service._job_store.list_running.return_value = [job]
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
    service._job_store.list_running.return_value = [job]
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
    service._job_store.list_running.return_value = [job]
    service._reconcile_recovery_checkpoint = MagicMock(
        side_effect=ValueError("Checkpoint is missing.")
    )

    recovered = service.recover_interrupted_jobs()

    assert recovered == 0
    assert job.status == GenerationJobStatus.RUNNING
    service._reconcile_recovery_checkpoint.assert_called_once()
    service._job_store.save.assert_not_called()


def test_interrupted_job_resume_persists_running_and_reserves_worker():
    service, validator = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)

    service._jobs[job.job_id] = job
    service._reconcile_recovery_checkpoint = MagicMock(return_value={})

    resumed = service.start_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert resumed is job
    assert job.status == GenerationJobStatus.RUNNING
    assert validator.calls == 1
    service._reconcile_recovery_checkpoint.assert_called_once()
    service._job_store.save.assert_called_once_with(job)
    assert (DATA_MODEL_ID, JOB_ID) in service._active_workers


def test_failed_resume_persistence_restores_interrupted_state():
    service, _ = build_service()
    job = make_job(GenerationJobStatus.INTERRUPTED)
    job.error = "Previous interruption detail"

    service._jobs[job.job_id] = job
    service._reconcile_recovery_checkpoint = MagicMock(return_value={})
    service._job_store.save.side_effect = OSError("Persistence unavailable")

    with pytest.raises(OSError, match="Persistence unavailable"):
        service.start_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    assert job.status == GenerationJobStatus.INTERRUPTED
    assert job.error == "Previous interruption detail"
    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers
