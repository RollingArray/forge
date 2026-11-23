import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
from fastapi import FastAPI

from app.api import generation as generation_api
from app.interfaces.auth_user import AuthUser
from app.models.generation_persistence import GenerationCheckpointManifest


USER = AuthUser(
    user_id="test-user",
    email="test@example.com",
    display_name="Test User",
)

DATA_MODEL_ID = "test-model"
JOB_ID = "test-job"


def make_checkpoint():
    timestamp = datetime(
        2026, 11, 23, 10, 0, tzinfo=timezone.utc
    )

    return GenerationCheckpointManifest(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        specification_hash="a" * 64,
        seed=42,
        chunk_size=100,
        algorithm_version="1",
        attempt_id="attempt-1",
        entities={
            "Customer": {
                "target_rows": 0,
                "chunks": [],
            }
        },
        created_at=timestamp,
        updated_at=timestamp,
    )


def configure_endpoint(
    monkeypatch,
    *,
    allowed=True,
    job=None,
    checkpoint=None,
):
    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(
            can_generate=lambda **kwargs: allowed
        ),
    )

    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(
            get_job=lambda **kwargs: job
        ),
    )

    monkeypatch.setattr(
        generation_api,
        "checkpoint_store",
        SimpleNamespace(
            get=lambda **kwargs: checkpoint
        ),
    )

    # Isolated FastAPI application using the real generation router.
    # No application startup recovery is triggered.
    app = FastAPI()
    app.include_router(
        generation_api.router,
        prefix="/api/v1",
    )

    app.dependency_overrides[
        generation_api.get_authenticated_user
    ] = lambda: USER

    return app


def request_checkpoint(app):
    async def make_request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            return await client.get(
                f"/api/v1/data-models/{DATA_MODEL_ID}"
                f"/generation/{JOB_ID}/checkpoint"
            )

    return asyncio.run(make_request())


def test_checkpoint_endpoint_serializes_manifest_as_json(
    monkeypatch,
):
    checkpoint = make_checkpoint()

    job = SimpleNamespace(
        data_model_id=DATA_MODEL_ID,
    )

    app = configure_endpoint(
        monkeypatch,
        job=job,
        checkpoint=checkpoint,
    )

    response = request_checkpoint(app)

    assert response.status_code == 200
    assert response.json() == checkpoint.model_dump(mode="json")


def test_checkpoint_endpoint_returns_404_when_checkpoint_is_missing(
    monkeypatch,
):
    job = SimpleNamespace(
        data_model_id=DATA_MODEL_ID,
    )

    app = configure_endpoint(
        monkeypatch,
        job=job,
        checkpoint=None,
    )

    response = request_checkpoint(app)

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Generation checkpoint not found."
    )


def test_checkpoint_endpoint_returns_404_when_access_is_denied(
    monkeypatch,
):
    app = configure_endpoint(
        monkeypatch,
        allowed=False,
    )

    response = request_checkpoint(app)

    assert response.status_code == 404
    assert response.json()["detail"] == "Data model not found."
