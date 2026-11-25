import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
from fastapi import FastAPI

from app.api import data_models as data_models_api
from app.interfaces.auth_user import AuthUser


USER = AuthUser(
    user_id="authenticated-owner",
    email="owner@example.com",
    display_name="Owner",
)

SOURCE_ID = "source-model"
DUPLICATE_ID = "duplicate-model"


def make_data_model():
    timestamp = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        data_model_id=DUPLICATE_ID,
        owner_user_id=USER.user_id,
        name=f"Copy of Aerospace Model - {SOURCE_ID}",
        description="Original description",
        color="#123456",
        tags=["aerospace", "test"],
        status="DRAFT",
        created_at=timestamp,
        updated_at=timestamp,
    )


def make_app(monkeypatch, duplicate_result=None):
    calls = []

    def duplicate_data_model(**kwargs):
        calls.append(kwargs)
        return duplicate_result

    monkeypatch.setattr(
        data_models_api,
        "data_model_service",
        SimpleNamespace(duplicate_data_model=duplicate_data_model),
    )

    app = FastAPI()
    app.include_router(data_models_api.router, prefix="/api/v1")
    app.dependency_overrides[
        data_models_api.get_authenticated_user
    ] = lambda: USER

    return app, calls


def post_duplicate(app):
    async def make_request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            return await client.post(
                f"/api/v1/data-models/{SOURCE_ID}/duplicate"
            )

    return asyncio.run(make_request())


def test_duplicate_endpoint_returns_created_model_and_201(monkeypatch):
    duplicated_model = make_data_model()
    app, calls = make_app(monkeypatch, duplicated_model)

    response = post_duplicate(app)

    assert response.status_code == 201
    payload = response.json()

    assert payload["data_model_id"] == DUPLICATE_ID
    assert payload["owner_user_id"] == USER.user_id
    assert payload["name"] == f"Copy of Aerospace Model - {SOURCE_ID}"
    assert payload["description"] == "Original description"
    assert payload["color"] == "#123456"
    assert payload["tags"] == ["aerospace", "test"]
    assert payload["status"] == "DRAFT"

    assert calls == [{
        "data_model_id": SOURCE_ID,
        "owner_user_id": USER.user_id,
    }]


def test_duplicate_endpoint_returns_404_when_service_returns_none(monkeypatch):
    app, calls = make_app(monkeypatch, duplicate_result=None)

    response = post_duplicate(app)

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Data model not found or its specification is missing."
    )
    assert calls == [{
        "data_model_id": SOURCE_ID,
        "owner_user_id": USER.user_id,
    }]


def test_duplicate_endpoint_does_not_require_request_body(monkeypatch):
    app, _ = make_app(monkeypatch, make_data_model())

    response = post_duplicate(app)

    assert response.status_code == 201
