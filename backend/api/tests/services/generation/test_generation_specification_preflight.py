from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.generation_model import (
    GenerationEntityProgress,
    GenerationJobResponse,
    GenerationJobStatus,
)
from app.services.generation_planner import (
    GenerationEntityPlan,
    GenerationPlan,
)
from app.services.generation_service import GenerationService
from app.services.specification_validation_error import (
    SpecificationValidationError,
)


DATA_MODEL_ID = "MODEL-TEST"
JOB_ID = "JOB-TEST"


class FakeSpecificationService:
    def __init__(self, specification):
        self.specification = specification

    def get_specification(self, *, data_model_id):
        return self.specification


class FakeValidationService:
    def __init__(self, can_continue, warnings=0):
        self.can_continue = can_continue
        self.warnings = warnings
        self.calls = 0

    def validate(self, specification):
        self.calls += 1
        return {
            "can_continue": self.can_continue,
            "errors": 0 if self.can_continue else 1,
            "warnings": self.warnings,
            "findings": [],
        }


def build_service(
    *,
    can_continue,
    warnings=0,
    specification=None,
):
    specification = specification or {
        "name": "Test Model",
        "generation": {"seed": 42},
        "entities": [],
    }

    specification_service = FakeSpecificationService(specification)
    validation_service = FakeValidationService(
        can_continue=can_continue,
        warnings=warnings,
    )

    planner = MagicMock()
    planner.build.return_value = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="ORGANIZATION",
                target_rows=10,
            ),
        ),
    )

    checkpoint_store = MagicMock()
    generation_log_store = MagicMock()

    service = GenerationService(
        specification_service=specification_service,
        generation_planner=planner,
        checkpoint_store=checkpoint_store,
        generation_log_store=generation_log_store,
        specification_validation_service=validation_service,
    )

    service._job_store = MagicMock()

    return (
        service,
        validation_service,
        planner,
        checkpoint_store,
        generation_log_store,
    )


def make_job(status):
    now = datetime.now(timezone.utc)

    return GenerationJobResponse(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        status=status,
        created_at=now,
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


def test_invalid_specification_rejects_job_creation_before_persistence():
    (
        service,
        validator,
        planner,
        checkpoint_store,
        log_store,
    ) = build_service(can_continue=False)

    with pytest.raises(SpecificationValidationError):
        service.create_job(
            data_model_id=DATA_MODEL_ID,
            user_id="USER-TEST",
        )

    validator_calls = validator.calls
    assert validator_calls == 1
    planner.build.assert_not_called()
    service._job_store.save.assert_not_called()
    log_store.create.assert_not_called()
    checkpoint_store.create_checkpoint.assert_not_called()


def test_warning_only_specification_allows_job_creation():
    (
        service,
        validator,
        planner,
        checkpoint_store,
        log_store,
    ) = build_service(
        can_continue=True,
        warnings=2,
    )

    job = service.create_job(
        data_model_id=DATA_MODEL_ID,
        user_id="USER-TEST",
    )

    assert job is not None
    assert job.status == GenerationJobStatus.CREATED
    assert validator.calls == 1
    planner.build.assert_called_once()
    service._job_store.save.assert_called_once()
    log_store.create.assert_called_once()
    checkpoint_store.create_checkpoint.assert_not_called()


def test_invalid_specification_blocks_created_job_before_lifecycle_changes():
    (
        service,
        validator,
        planner,
        checkpoint_store,
        log_store,
    ) = build_service(can_continue=False)

    job = make_job(GenerationJobStatus.CREATED)
    service._jobs[job.job_id] = job

    with pytest.raises(SpecificationValidationError):
        service.start_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    assert validator.calls == 1
    assert job.status == GenerationJobStatus.CREATED
    planner.build.assert_not_called()
    service._job_store.save.assert_not_called()
    log_store.append.assert_not_called()
    checkpoint_store.create_checkpoint.assert_not_called()


def test_invalid_specification_blocks_interrupted_job_before_reconciliation():
    (
        service,
        validator,
        planner,
        checkpoint_store,
        log_store,
    ) = build_service(can_continue=False)

    job = make_job(GenerationJobStatus.INTERRUPTED)
    service._jobs[job.job_id] = job

    service._reconcile_recovery_checkpoint = MagicMock()

    with pytest.raises(SpecificationValidationError):
        service.start_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    assert validator.calls == 1
    assert job.status == GenerationJobStatus.INTERRUPTED
    service._reconcile_recovery_checkpoint.assert_not_called()
    planner.build.assert_not_called()
    service._job_store.save.assert_not_called()
    log_store.append.assert_not_called()
    checkpoint_store.create_checkpoint.assert_not_called()


def test_invalid_specification_blocks_generation_readiness_before_planning():
    (
        service,
        validator,
        planner,
        checkpoint_store,
        log_store,
    ) = build_service(can_continue=False)

    with pytest.raises(SpecificationValidationError):
        service.get_readiness(data_model_id=DATA_MODEL_ID)

    assert validator.calls == 1
    planner.build.assert_not_called()

