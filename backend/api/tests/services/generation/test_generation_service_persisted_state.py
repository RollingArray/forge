from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.models.generation_model import (
    GenerationEntityProgress,
    GenerationJobRecord,
    GenerationJobResponse,
    GenerationJobStatus,
)
from app.services.generation_service import GenerationService


DATA_MODEL_ID = "MODEL-TEST"
OTHER_DATA_MODEL_ID = "MODEL-OTHER"
JOB_ID = "JOB-TEST"


def make_job(
    data_model_id: str = DATA_MODEL_ID,
    status: GenerationJobStatus = GenerationJobStatus.CREATED,
) -> GenerationJobRecord:
    return GenerationJobRecord(
        data_model_id=data_model_id,
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
                chunk_size=50,
            )
        ],
    )


def build_service() -> GenerationService:
    service = GenerationService(
        specification_service=MagicMock(),
        checkpoint_store=MagicMock(),
        generation_log_store=MagicMock(),
    )
    service._job_store = MagicMock()
    service._validation_store = MagicMock()
    service._quality_store = MagicMock()
    return service


def test_internal_job_read_uses_persisted_state_over_stale_cache():
    service = build_service()
    cached = make_job(status=GenerationJobStatus.RUNNING)
    persisted = make_job(status=GenerationJobStatus.INTERRUPTED)

    service._jobs[JOB_ID] = cached
    service._job_store.get.return_value = persisted

    result = service._get_or_load_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert result is persisted
    assert result.status == GenerationJobStatus.INTERRUPTED
    assert service._jobs[JOB_ID] is persisted
    service._job_store.get.assert_called_once_with(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )


def test_internal_job_read_does_not_resurrect_missing_persisted_job():
    service = build_service()
    service._jobs[JOB_ID] = make_job()
    service._job_store.get.return_value = None

    result = service._get_or_load_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert result is None
    assert JOB_ID not in service._jobs


def test_internal_job_read_rejects_job_from_another_data_model():
    service = build_service()
    service._jobs[JOB_ID] = make_job()
    service._job_store.get.return_value = make_job(
        data_model_id=OTHER_DATA_MODEL_ID,
    )

    result = service._get_or_load_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert result is None
    assert JOB_ID not in service._jobs


def test_public_job_read_uses_persisted_state_over_stale_cache():
    service = build_service()
    cached = make_job(status=GenerationJobStatus.RUNNING)
    persisted = make_job(status=GenerationJobStatus.INTERRUPTED)

    service._jobs[JOB_ID] = cached
    service._job_store.get.return_value = persisted

    result = service.get_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert result is persisted
    assert result.status == GenerationJobStatus.INTERRUPTED
    assert service._jobs[JOB_ID] is persisted
    service._job_store.get.assert_called_once_with(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )


def test_public_job_read_does_not_return_cached_job_when_persisted_record_missing():
    service = build_service()
    service._jobs[JOB_ID] = make_job()
    service._job_store.get.return_value = None

    result = service.get_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert result is None
    assert JOB_ID not in service._jobs


def test_public_job_read_rejects_persisted_job_from_another_data_model():
    service = build_service()
    service._jobs[JOB_ID] = make_job()
    service._job_store.get.return_value = make_job(
        data_model_id=OTHER_DATA_MODEL_ID,
    )

    result = service.get_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert result is None
    assert JOB_ID not in service._jobs
