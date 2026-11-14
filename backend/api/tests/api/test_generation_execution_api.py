import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import generation as generation_api
from app.interfaces.auth_user import AuthUser
from app.models.generation_model import (
    GenerationEntityStatus,
    GenerationJobStatus,
)

USER = AuthUser(
    user_id="test-user",
    email="test@example.com",
    display_name="Test User",
)

DATA_MODEL_ID = "test-model"
JOB_ID = "test-job"


def make_entity(status):
    return SimpleNamespace(status=status)


def make_job(**overrides):
    values = {
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "status": GenerationJobStatus.COMPLETED,
        "total_target_rows": 100,
        "total_generated_rows": 100,
        "elapsed_seconds": 10.0,
        "peak_memory_mb": 128.5,
        "entities": [
            make_entity(GenerationEntityStatus.COMPLETED),
            make_entity(GenerationEntityStatus.COMPLETED),
        ],
        # Deliberately present on the persisted job, but not in the summary.
        "error": "internal detail",
        "created_at": datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc),
        "started_at": datetime(2026, 11, 14, 10, 0, 1, tzinfo=timezone.utc),
        "completed_at": datetime(2026, 11, 14, 10, 0, 11, tzinfo=timezone.utc),
        "validation": {"internal": "validation detail"},
        "quality": {"internal": "quality detail"},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def configure_access(monkeypatch, allowed=True):
    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: allowed),
    )


def invoke(job, monkeypatch):
    configure_access(monkeypatch)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(get_job=lambda **kwargs: job),
    )
    return asyncio.run(
        generation_api.get_generation_execution_summary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )


def test_execution_summary_returns_only_required_summary_fields(monkeypatch):
    response = invoke(make_job(), monkeypatch)
    result = response.model_dump()

    assert result == {
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "status": "COMPLETED",
        "total_target_rows": 100,
        "total_generated_rows": 100,
        "elapsed_seconds": 10.0,
        "peak_memory_mb": 128.5,
        "entity_count": 2,
        "completed_entity_count": 2,
        "failed_entity_count": 0,
        "throughput_rows_per_second": 10.0,
    }

    for excluded in (
        "entities",
        "error",
        "created_at",
        "started_at",
        "completed_at",
        "progress",
        "validation",
        "quality",
    ):
        assert excluded not in result


def test_execution_summary_counts_each_entity_status_correctly(monkeypatch):
    job = make_job(
        status=GenerationJobStatus.PARTIALLY_COMPLETED,
        entities=[
            make_entity(GenerationEntityStatus.COMPLETED),
            make_entity(GenerationEntityStatus.FAILED),
            make_entity(GenerationEntityStatus.RUNNING),
            make_entity(GenerationEntityStatus.QUEUED),
            make_entity(GenerationEntityStatus.NOT_STARTED),
            make_entity(GenerationEntityStatus.CANCELLED),
        ],
    )

    response = invoke(job, monkeypatch)

    assert response.status == GenerationJobStatus.PARTIALLY_COMPLETED
    assert response.entity_count == 6
    assert response.completed_entity_count == 1
    assert response.failed_entity_count == 1


def test_execution_summary_handles_empty_entity_list(monkeypatch):
    response = invoke(make_job(entities=[]), monkeypatch)

    assert response.entity_count == 0
    assert response.completed_entity_count == 0
    assert response.failed_entity_count == 0


@pytest.mark.parametrize(
    "job_status",
    [
        GenerationJobStatus.RUNNING,
        GenerationJobStatus.PARTIALLY_COMPLETED,
        GenerationJobStatus.FAILED,
        GenerationJobStatus.CANCELLED,
    ],
)
def test_execution_summary_preserves_job_status(monkeypatch, job_status):
    response = invoke(make_job(status=job_status), monkeypatch)

    assert response.status == job_status


@pytest.mark.parametrize(
    ("generated_rows", "elapsed_seconds", "expected_throughput"),
    [
        (100, 10.0, 10.0),
        (50, 10.0, 5.0),
        (0, 10.0, None),
        (100, 0.0, None),
        (100, None, None),
    ],
)
def test_execution_summary_throughput_handles_edge_cases(
    monkeypatch,
    generated_rows,
    elapsed_seconds,
    expected_throughput,
):
    job = make_job(
        total_generated_rows=generated_rows,
        elapsed_seconds=elapsed_seconds,
    )

    response = invoke(job, monkeypatch)

    assert response.throughput_rows_per_second == expected_throughput


def test_execution_summary_returns_404_when_access_is_denied(monkeypatch):
    configure_access(monkeypatch, allowed=False)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(
            get_job=lambda **kwargs: pytest.fail(
                "Job lookup must not occur when access is denied."
            )
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_execution_summary(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Data model not found."


def test_execution_summary_returns_404_when_job_is_missing(monkeypatch):
    configure_access(monkeypatch)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(get_job=lambda **kwargs: None),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_execution_summary(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."


def test_execution_summary_returns_404_for_mismatched_data_model(monkeypatch):
    job = make_job(data_model_id="another-model")
    configure_access(monkeypatch)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(get_job=lambda **kwargs: job),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_execution_summary(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."
