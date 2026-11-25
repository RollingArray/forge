from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.generation_service as generation_service_module
from app.constants.generation import DEFAULT_GENERATION_CHUNK_SIZE
from app.models.generation_model import (
    GenerationEntityProgress,
    GenerationJobRecord,
    GenerationJobResponse,
    GenerationJobStatus,
    GenerationLifecyclePhase,
)
from app.models.generation_persistence import (
    GenerationFinalizationStatus,
)
from app.services.generation_job_control_store import (
    GenerationJobControlRequest,
    GenerationJobControlStore,
)
from app.services.generation_job_store import GenerationJobStore
from app.services.generation_service import GenerationService


DATA_MODEL_ID = "MODEL-CONTROL-TEST"
JOB_ID = "JOB-CONTROL-TEST"
ATTEMPT_ID = "control-attempt-001"

SPECIFICATION = {
    "name": "Generation Control Test",
    "generation": {"seed": 42},
    "entities": [],
}


class FakeSpecificationService:
    def get_specification(self, *, data_model_id):
        assert data_model_id == DATA_MODEL_ID
        return SPECIFICATION


class FakePlanner:
    def build(self, *, specification):
        return SimpleNamespace(
            entities=[
                SimpleNamespace(
                    entity_name="ORGANIZATION",
                    target_rows=10,
                )
            ]
        )


class FakeRunService:
    """Invoke the real service callback at a committed chunk boundary."""

    def __init__(self, **kwargs):
        pass

    def run(self, **kwargs):
        kwargs["on_chunk_completed"](
            "ORGANIZATION",
            1,
            2,
            5,
            [{"ID": index} for index in range(5)],
            0.25,
            1.0,
            [],
            [],
        )


def make_running_job():
    response = GenerationJobResponse(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        status=GenerationJobStatus.RUNNING,
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

    data = response.model_dump(
        exclude={"throughput_rows_per_second"}
    )
    data["attempt_id"] = ATTEMPT_ID

    job = GenerationJobRecord.model_validate(data)
    job.lifecycle_phase = GenerationLifecyclePhase.GENERATING
    return job


def make_checkpoint():
    committed_chunk = SimpleNamespace(
        chunk_number=1,
        row_start=0,
        row_count=5,
    )

    entity = SimpleNamespace(
        target_rows=10,
        committed_rows=5,
        chunks=[committed_chunk],
        finalization=SimpleNamespace(status=GenerationFinalizationStatus.PENDING),
    )

    return SimpleNamespace(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        chunk_size=DEFAULT_GENERATION_CHUNK_SIZE,
        updated_at=datetime.now(timezone.utc),
        entities={"ORGANIZATION": entity},
    )


@pytest.mark.parametrize(
    ("control_request", "expected_status"),
    [
        (
            GenerationJobControlRequest.PAUSE,
            GenerationJobStatus.PAUSED,
        ),
        (
            GenerationJobControlRequest.CANCEL,
            GenerationJobStatus.CANCELLED,
        ),
    ],
)
def test_control_request_stops_after_committed_chunk_and_persists_state(
    tmp_path,
    monkeypatch,
    control_request,
    expected_status,
):
    job_store = GenerationJobStore()
    job_store._root = tmp_path

    control_store = GenerationJobControlStore()
    control_store._root = tmp_path

    checkpoint = make_checkpoint()
    checkpoint_store = MagicMock()
    checkpoint_store.get.return_value = checkpoint

    event_broker = MagicMock()
    event_broker.diagnostics_enabled = False

    service = GenerationService(
        specification_service=FakeSpecificationService(),
        generation_planner=FakePlanner(),
        checkpoint_store=checkpoint_store,
        event_broker=event_broker,
        generation_log_store=MagicMock(),
    )

    service._job_store = job_store
    service._control_store = control_store

    job = make_running_job()
    job_store.save(job)

    control_store.request(
        DATA_MODEL_ID,
        JOB_ID,
        control_request,
    )

    monkeypatch.setattr(
        generation_service_module,
        "GenerationRunService",
        FakeRunService,
    )

    service._execute_job_reserved(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    persisted_job = job_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert persisted_job is not None
    assert persisted_job.status == expected_status
    assert persisted_job.total_generated_rows == 5
    assert persisted_job.progress == 0.5
    assert persisted_job.error is None

    persisted_entity = persisted_job.entities[0]
    assert persisted_entity.generated_rows == 5
    assert persisted_entity.completed_chunks == 1
    assert len(persisted_entity.chunks) == 1
    assert persisted_entity.chunks[0].chunk_number == 1
    assert persisted_entity.chunks[0].generated_rows == 5

    # The committed checkpoint evidence remains authoritative and unchanged.
    reloaded_checkpoint = checkpoint_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )
    assert reloaded_checkpoint.entities["ORGANIZATION"].committed_rows == 5
    assert len(reloaded_checkpoint.entities["ORGANIZATION"].chunks) == 1

    # The request is cleared only after the resulting job state is saved.
    assert control_store.get_request(DATA_MODEL_ID, JOB_ID) is None

    event_types = [
        call.kwargs["event_type"]
        for call in event_broker.publish.call_args_list
    ]
    assert "CHUNK_COMMITTED" in event_types
    assert (
        "GENERATION_PAUSED"
        if expected_status == GenerationJobStatus.PAUSED
        else "GENERATION_CANCELLED"
    ) in event_types


@pytest.mark.parametrize(
    "control_request",
    [
        GenerationJobControlRequest.PAUSE,
        GenerationJobControlRequest.CANCEL,
    ],
)
def test_control_request_is_retained_when_status_persistence_fails(
    tmp_path,
    monkeypatch,
    control_request,
):
    job_store = GenerationJobStore()
    job_store._root = tmp_path

    control_store = GenerationJobControlStore()
    control_store._root = tmp_path

    checkpoint_store = MagicMock()
    checkpoint_store.get.return_value = make_checkpoint()

    event_broker = MagicMock()
    event_broker.diagnostics_enabled = False

    service = GenerationService(
        specification_service=FakeSpecificationService(),
        generation_planner=FakePlanner(),
        checkpoint_store=checkpoint_store,
        event_broker=event_broker,
        generation_log_store=MagicMock(),
    )
    service._job_store = job_store
    service._control_store = control_store

    job_store.save(make_running_job())

    control_store.request(
        DATA_MODEL_ID,
        JOB_ID,
        control_request,
    )

    original_save = job_store.save
    save_count = 0

    def fail_status_save(job):
        nonlocal save_count
        save_count += 1

        # The first save persists the committed chunk projection.
        # The second save attempts to persist PAUSED or CANCELLED.
        if save_count == 2:
            raise RuntimeError("Simulated status persistence failure.")

        original_save(job)

    monkeypatch.setattr(job_store, "save", fail_status_save)
    monkeypatch.setattr(
        generation_service_module,
        "GenerationRunService",
        FakeRunService,
    )

    # The service handles execution failures internally and persists
    # a recovered job state rather than propagating the exception.
    service._execute_job_reserved(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    persisted_job = job_store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert persisted_job is not None

    # The requested PAUSED/CANCELLED transition was not persisted.
    # Recovery must not falsely report that requested state.
    assert persisted_job.status == GenerationJobStatus.FAILED
    assert persisted_job.total_generated_rows == 5
    assert "Simulated status persistence failure" in persisted_job.error

    # The durable request must survive because the requested state
    # was not successfully persisted.
    assert control_store.get_request(
        DATA_MODEL_ID,
        JOB_ID,
    ) == control_request


@pytest.mark.parametrize(
    ("method_name", "control_request"),
    [
        ("pause_job", GenerationJobControlRequest.PAUSE),
        ("cancel_job", GenerationJobControlRequest.CANCEL),
    ],
)
def test_control_service_methods_persist_requests(
    tmp_path,
    method_name,
    control_request,
):
    job_store = GenerationJobStore()
    job_store._root = tmp_path

    control_store = GenerationJobControlStore()
    control_store._root = tmp_path

    service = GenerationService(
        generation_log_store=MagicMock(),
    )
    service._job_store = job_store
    service._control_store = control_store

    job_store.save(make_running_job())

    result = getattr(service, method_name)(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert result.status == GenerationJobStatus.RUNNING
    assert control_store.get_request(
        DATA_MODEL_ID,
        JOB_ID,
    ) == control_request


@pytest.mark.parametrize(
    ("method_name", "job_status"),
    [
        ("pause_job", GenerationJobStatus.PAUSED),
        ("pause_job", GenerationJobStatus.COMPLETED),
        ("cancel_job", GenerationJobStatus.CANCELLED),
        ("cancel_job", GenerationJobStatus.FAILED),
    ],
)
def test_control_service_methods_reject_non_running_jobs(
    tmp_path,
    method_name,
    job_status,
):
    job_store = GenerationJobStore()
    job_store._root = tmp_path

    control_store = GenerationJobControlStore()
    control_store._root = tmp_path

    service = GenerationService(
        generation_log_store=MagicMock(),
    )
    service._job_store = job_store
    service._control_store = control_store

    job = make_running_job()
    job.status = job_status
    job_store.save(job)

    with pytest.raises(
        ValueError,
        match="Only RUNNING jobs accept controls",
    ):
        getattr(service, method_name)(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    assert control_store.get_request(
        DATA_MODEL_ID,
        JOB_ID,
    ) is None


def test_control_service_methods_reject_missing_job(tmp_path):
    job_store = GenerationJobStore()
    job_store._root = tmp_path

    control_store = GenerationJobControlStore()
    control_store._root = tmp_path

    service = GenerationService(
        generation_log_store=MagicMock(),
    )
    service._job_store = job_store
    service._control_store = control_store

    with pytest.raises(
        ValueError,
        match="Generation job not found",
    ):
        service.pause_job(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
        )

    assert control_store.get_request(
        DATA_MODEL_ID,
        JOB_ID,
    ) is None
