import asyncio
import json
from types import SimpleNamespace

import pytest

from fastapi import FastAPI

from app.api import generation as generation_api
from app.interfaces.auth_user import AuthUser
from app.services.generation_event_broker import GenerationEventBroker


USER = AuthUser(
    user_id="test-user",
    email="test@example.com",
    display_name="Test User",
)

DATA_MODEL_ID = "test-model"
JOB_ID = "test-job"


def make_job(status="RUNNING"):
    payload = {
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "status": status,
    }

    return SimpleNamespace(
        data_model_id=DATA_MODEL_ID,
        status=status,
        model_dump_json=lambda: json.dumps(payload),
    )


def configure_events_endpoint(monkeypatch, get_job, broker):
    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(get_job=get_job),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_event_broker",
        broker,
    )

    app = FastAPI()
    app.include_router(generation_api.router, prefix="/api/v1")
    app.dependency_overrides[
        generation_api.get_authenticated_user
    ] = lambda: USER

    return app


def test_events_endpoint_subscribes_before_refreshed_snapshot(
    monkeypatch,
):
    async def scenario():
        broker = GenerationEventBroker()
        job = make_job()
        calls = 0

        def get_job(**kwargs):
            nonlocal calls
            calls += 1

            if calls == 2:
                # This publication happens after subscription but during
                # the refreshed snapshot lookup.
                broker.publish(
                    data_model_id=DATA_MODEL_ID,
                    job_id=JOB_ID,
                    event_type="GENERATION_ACTIVITY",
                    data={"stage": "ENTITY_GENERATION"},
                )

            return job

        configure_events_endpoint(monkeypatch, get_job, broker)

        response = await generation_api.stream_generation_events(
            DATA_MODEL_ID,
            JOB_ID,
            USER,
        )

        iterator = response.body_iterator

        snapshot = await anext(iterator)
        assert "event: JOB_SNAPSHOT" in snapshot

        activity = await asyncio.wait_for(
            anext(iterator),
            timeout=2.0,
        )
        assert "event: GENERATION_ACTIVITY" in activity
        assert "ENTITY_GENERATION" in activity

        broker.publish(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            event_type="GENERATION_COMPLETED",
            data={"status": "COMPLETED"},
        )

        terminal = await asyncio.wait_for(
            anext(iterator),
            timeout=2.0,
        )
        assert "event: GENERATION_COMPLETED" in terminal

        with pytest.raises(StopAsyncIteration):
            await anext(iterator)

        assert (DATA_MODEL_ID, JOB_ID) not in broker._subscribers

    asyncio.run(scenario())


def test_events_endpoint_unsubscribes_for_terminal_snapshot(
    monkeypatch,
):
    async def scenario():
        broker = GenerationEventBroker()
        calls = 0

        def get_job(**kwargs):
            nonlocal calls
            calls += 1
            return make_job(
                "RUNNING" if calls == 1 else "COMPLETED"
            )

        configure_events_endpoint(monkeypatch, get_job, broker)

        response = await generation_api.stream_generation_events(
            DATA_MODEL_ID,
            JOB_ID,
            USER,
        )

        iterator = response.body_iterator

        snapshot = await anext(iterator)
        assert "event: JOB_SNAPSHOT" in snapshot
        assert "COMPLETED" in snapshot

        with pytest.raises(StopAsyncIteration):
            await anext(iterator)

        assert (DATA_MODEL_ID, JOB_ID) not in broker._subscribers

    asyncio.run(scenario())
