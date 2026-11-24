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
