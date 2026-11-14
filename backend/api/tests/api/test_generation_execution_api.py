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


def make_job(**overrides):
    values = {
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "status": GenerationJobStatus.COMPLETED,
        "error": None,
        "created_at": datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc),
        "started_at": datetime(2026, 11, 14, 10, 0, 1, tzinfo=timezone.utc),
        "completed_at": datetime(2026, 11, 14, 10, 0, 11, tzinfo=timezone.utc),
        "total_target_rows": 100,
        "total_generated_rows": 100,
        "progress": 1.0,
        "elapsed_seconds": 10.0,
        "peak_memory_mb": 128.5,
        "entities": [
            SimpleNamespace(
                entity_name="ORGANIZATION",
                target_rows=100,
                generated_rows=100,
                completed_chunks=2,
                total_chunks=2,
                status=GenerationEntityStatus.COMPLETED,
                elapsed_seconds=8.0,
                throughput_rows_per_second=12.5,
                peak_memory_mb=96.0,
                chunks=[{"internal": "detail"}],
                vocabulary_semantic_calls=[{"internal": "detail"}],
            )
        ],
        "validation": {"valid": True},
        "quality": {"population_fidelity": {"score": 1.0}},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def configure_access(monkeypatch, allowed=True):
    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: allowed),
    )


def test_get_generation_execution_returns_execution_projection(monkeypatch):
    job = make_job()
    configure_access(monkeypatch)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(get_job=lambda **kwargs: job),
    )

    response = asyncio.run(
        generation_api.get_generation_execution(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    result = response.model_dump()

    assert response.data_model_id == DATA_MODEL_ID
    assert response.job_id == JOB_ID
    assert response.status == GenerationJobStatus.COMPLETED
    assert response.total_target_rows == 100
    assert response.total_generated_rows == 100
    assert response.elapsed_seconds == 10.0
    assert response.throughput_rows_per_second == 10.0

    assert len(response.entities) == 1
    entity = result["entities"][0]
    assert entity["entity_name"] == "ORGANIZATION"
    assert entity["completed_chunks"] == 2
    assert entity["total_chunks"] == 2
    assert entity["throughput_rows_per_second"] == 12.5

    assert "validation" not in result
    assert "quality" not in result
    assert "chunks" not in entity
    assert "vocabulary_semantic_calls" not in entity


def test_get_generation_execution_returns_404_when_access_is_denied(
    monkeypatch,
):
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
            generation_api.get_generation_execution(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Data model not found."


def test_get_generation_execution_returns_404_when_job_is_missing(
    monkeypatch,
):
    configure_access(monkeypatch)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(get_job=lambda **kwargs: None),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_execution(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."


def test_get_generation_execution_returns_404_for_mismatched_data_model(
    monkeypatch,
):
    job = make_job(data_model_id="another-model")
    configure_access(monkeypatch)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(get_job=lambda **kwargs: job),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_execution(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."
