from contextlib import nullcontext
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import app.services.generation_service as generation_service_module
from app.constants.generation import DEFAULT_GENERATION_CHUNK_SIZE
from app.models.generation_model import (
    GenerationEntityProgress,
    GenerationJobRecord,
    GenerationJobStatus,
)
from app.services.generation_job_store import GenerationJobStore
from app.services.generation_service import GenerationService


DATA_MODEL_ID = "MODEL-START-TEST"
JOB_ID = "JOB-START-TEST"

SPECIFICATION = {
    "name": "Generation Start Test",
    "generation": {"seed": 42},
    "entities": [],
}


class FakeSpecificationService:
    def get_specification(self, *, data_model_id):
        assert data_model_id == DATA_MODEL_ID
        return SPECIFICATION


class FakeValidationService:
    def validate(self, specification):
        return {
            "can_continue": True,
            "errors": 0,
            "warnings": 0,
            "findings": [],
        }


def make_created_job():
    return GenerationJobRecord(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        status=GenerationJobStatus.CREATED,
        created_at=datetime.now(timezone.utc),
        total_target_rows=10,
        total_generated_rows=0,
        progress=0.0,
        entities=[
            GenerationEntityProgress(
                entity_name="ORGANIZATION",
                target_rows=10,
                chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
                total_chunks=1,
            )
        ],
    )


def build_start_service(tmp_path, monkeypatch):
    job_store = GenerationJobStore()
    monkeypatch.setattr(job_store, "_root", tmp_path)

    planner = MagicMock()
    planner.build.return_value = MagicMock(
        entities=[
            MagicMock(
                entity_name="ORGANIZATION",
                target_rows=10,
            )
        ]
    )

    checkpoint_store = MagicMock()
    checkpoint_store.get.return_value = None

    event_broker = MagicMock()
    event_broker.diagnostics_enabled = False

    service = GenerationService(
        specification_service=FakeSpecificationService(),
        generation_planner=planner,
        checkpoint_store=checkpoint_store,
        event_broker=event_broker,
        generation_log_store=MagicMock(),
        specification_validation_service=FakeValidationService(),
    )
    service._job_store = job_store

    # Keep the test focused on start lifecycle behaviour. The job store
    # remains real and file-backed; only the execution lease acquisition
    # is isolated from the machine's application data directory.
    monkeypatch.setattr(
        generation_service_module,
        "generation_execution_lease",
        lambda *args, **kwargs: nullcontext(),
    )

    job_store.save(make_created_job())

    return service, job_store, checkpoint_store, event_broker


def test_checkpoint_initialization_failure_is_durably_recorded_as_failed(
    tmp_path,
    monkeypatch,
):
    service, job_store, checkpoint_store, event_broker = (
        build_start_service(tmp_path, monkeypatch)
    )

    checkpoint_store.initialize.side_effect = RuntimeError(
        "Simulated checkpoint initialization failure."
    )

    result = service.start_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert result is not None
    assert result.status == GenerationJobStatus.FAILED
    assert result.error == (
        "Simulated checkpoint initialization failure."
    )
    assert result.completed_at is not None

    persisted = job_store.get(DATA_MODEL_ID, JOB_ID)

    assert persisted is not None
    assert persisted.status == GenerationJobStatus.FAILED
    assert persisted.error == (
        "Simulated checkpoint initialization failure."
    )
    assert persisted.completed_at is not None
    assert persisted.attempt_id == result.attempt_id

    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers

    event_broker.publish.assert_called_once()
    event_data = event_broker.publish.call_args.kwargs["data"]
    assert event_data["status"] == GenerationJobStatus.FAILED.value

    checkpoint_store.initialize.assert_called_once()


def test_checkpoint_failure_propagates_when_failed_state_cannot_be_persisted(
    tmp_path,
    monkeypatch,
):
    service, job_store, checkpoint_store, _ = build_start_service(
        tmp_path,
        monkeypatch,
    )

    checkpoint_store.initialize.side_effect = RuntimeError(
        "Simulated checkpoint initialization failure."
    )

    original_save = job_store.save
    save_calls = 0

    def fail_terminal_save(job):
        nonlocal save_calls
        save_calls += 1

        if save_calls == 2:
            assert job.status == GenerationJobStatus.FAILED
            raise OSError("Simulated terminal persistence failure.")

        original_save(job)

    monkeypatch.setattr(job_store, "save", fail_terminal_save)

    with pytest.raises(
        OSError,
        match="Simulated terminal persistence failure",
    ):
        service.start_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    assert save_calls == 2

    persisted = job_store.get(DATA_MODEL_ID, JOB_ID)

    assert persisted is not None
    assert persisted.status == GenerationJobStatus.PREPARING
    assert persisted.error is None

    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers


def test_duplicate_start_rejects_existing_active_worker_without_mutation(
    tmp_path,
    monkeypatch,
):
    service, job_store, checkpoint_store, _ = build_start_service(
        tmp_path,
        monkeypatch,
    )

    job = job_store.get(DATA_MODEL_ID, JOB_ID)
    assert job is not None

    job.status = GenerationJobStatus.RUNNING
    job.attempt_id = "existing-attempt-001"
    job.started_at = datetime.now(timezone.utc)
    job_store.save(job)

    worker_key = (DATA_MODEL_ID, JOB_ID)
    service._active_workers.add(worker_key)

    with pytest.raises(
        ValueError,
        match="already has a scheduled or active worker",
    ):
        service.start_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    persisted = job_store.get(DATA_MODEL_ID, JOB_ID)

    assert persisted is not None
    assert persisted.status == GenerationJobStatus.RUNNING
    assert persisted.attempt_id == "existing-attempt-001"
    assert persisted.started_at == job.started_at

    # The duplicate request must not disturb the original worker reservation.
    assert worker_key in service._active_workers

    # It must not initialize or replace the original execution checkpoint.
    checkpoint_store.initialize.assert_not_called()


def _prepare_job_for_execution(job_store, status=GenerationJobStatus.PREPARING):
    job = job_store.get(DATA_MODEL_ID, JOB_ID)
    assert job is not None

    job.status = status
    job.attempt_id = "attempt-generation-start-test"
    job.started_at = datetime.now(timezone.utc)
    job_store.save(job)

    return job


def _prepare_execution_service(service, monkeypatch):
    service._active_workers.add((DATA_MODEL_ID, JOB_ID))

    # Isolate this test from checkpoint implementation details. The test
    # concerns only the durable status transition and its SSE publication.
    monkeypatch.setattr(
        service,
        "_validate_recovery_checkpoint",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        service,
        "_execute_job_reserved",
        lambda **kwargs: None,
    )


def test_execute_job_publishes_started_after_running_is_persisted(
    tmp_path,
    monkeypatch,
):
    service, job_store, _, event_broker = build_start_service(
        tmp_path,
        monkeypatch,
    )
    job = _prepare_job_for_execution(job_store)
    _prepare_execution_service(service, monkeypatch)

    def assert_running_is_already_durable(**kwargs):
        persisted = job_store.get(DATA_MODEL_ID, JOB_ID)
        assert persisted is not None
        assert persisted.status == GenerationJobStatus.RUNNING

    event_broker.publish.side_effect = assert_running_is_already_durable

    service.execute_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        attempt_id=job.attempt_id,
    )

    event_broker.publish.assert_called_once()
    published = event_broker.publish.call_args.kwargs

    assert published["event_type"] == "GENERATION_STARTED"
    assert published["data"]["status"] == GenerationJobStatus.RUNNING.value
    assert "attempt_id" not in published["data"]
    assert "preparation_phase" not in published["data"]
    assert "lifecycle_phase" not in published["data"]
    assert "resume_intent" not in published["data"]

    persisted = job_store.get(DATA_MODEL_ID, JOB_ID)
    assert persisted is not None
    assert persisted.status == GenerationJobStatus.RUNNING


def test_execute_job_does_not_publish_duplicate_started_event_for_running_job(
    tmp_path,
    monkeypatch,
):
    service, job_store, _, event_broker = build_start_service(
        tmp_path,
        monkeypatch,
    )
    job = _prepare_job_for_execution(
        job_store,
        status=GenerationJobStatus.RUNNING,
    )
    _prepare_execution_service(service, monkeypatch)

    service.execute_job(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        attempt_id=job.attempt_id,
    )

    event_broker.publish.assert_not_called()

    persisted = job_store.get(DATA_MODEL_ID, JOB_ID)
    assert persisted is not None
    assert persisted.status == GenerationJobStatus.RUNNING


def test_execute_job_does_not_publish_started_when_running_save_fails(
    tmp_path,
    monkeypatch,
):
    service, job_store, _, event_broker = build_start_service(
        tmp_path,
        monkeypatch,
    )
    job = _prepare_job_for_execution(job_store)
    _prepare_execution_service(service, monkeypatch)

    original_save = job_store.save

    def fail_running_save(candidate):
        if candidate.status == GenerationJobStatus.RUNNING:
            raise OSError("Simulated RUNNING persistence failure.")
        original_save(candidate)

    monkeypatch.setattr(job_store, "save", fail_running_save)

    with pytest.raises(
        OSError,
        match="Simulated RUNNING persistence failure",
    ):
        service.execute_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            attempt_id=job.attempt_id,
        )

    event_broker.publish.assert_not_called()

    persisted = job_store.get(DATA_MODEL_ID, JOB_ID)
    assert persisted is not None
    assert persisted.status == GenerationJobStatus.PREPARING
    assert (DATA_MODEL_ID, JOB_ID) not in service._active_workers
