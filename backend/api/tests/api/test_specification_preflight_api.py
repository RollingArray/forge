import asyncio
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api import generation as generation_api
from app.api import specification as specification_api
from app.constants.activity import ActivityType
from app.interfaces.auth_user import AuthUser
from app.models.generation_model import GenerationJobStatus
from app.models.specification_field_model import (
    CreateFieldRequest,
    UpdateFieldRequest,
)
from app.services.specification_validation_error import (
    SpecificationValidationError,
)


USER = AuthUser(
    user_id="test-user",
    email="test@example.com",
    display_name="Test User",
)

DATA_MODEL_ID = "test-model"
ENTITY_NAME = "ORGANIZATION"
FINDINGS = [
    {
        "severity": "ERROR",
        "message": "Invalid specification.",
    }
]
VALIDATION_RESULT = {
    "can_continue": False,
    "errors": 1,
    "warnings": 0,
    "findings": FINDINGS,
}
VALIDATION_ERROR = SpecificationValidationError(VALIDATION_RESULT)


def assert_validation_422(call):
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(call())

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == VALIDATION_RESULT


def test_create_field_returns_422_for_invalid_candidate(monkeypatch):
    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(can_edit=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_service",
        SimpleNamespace(
            create_field=lambda **kwargs: (_ for _ in ()).throw(
                VALIDATION_ERROR
            )
        ),
    )

    request = CreateFieldRequest.model_validate({
        "name": "DESCRIPTION",
        "type": "STRING",
    })

    assert_validation_422(
        lambda: specification_api.create_field(
            data_model_id=DATA_MODEL_ID,
            entity_name=ENTITY_NAME,
            request=request,
            user=USER,
        )
    )


def test_update_field_returns_422_for_invalid_candidate(monkeypatch):
    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(can_edit=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_service",
        SimpleNamespace(
            update_field=lambda **kwargs: (_ for _ in ()).throw(
                VALIDATION_ERROR
            )
        ),
    )

    request = UpdateFieldRequest.model_validate({
        "name": "UPDATED_NAME",
    })

    assert_validation_422(
        lambda: specification_api.update_field(
            data_model_id=DATA_MODEL_ID,
            entity_name=ENTITY_NAME,
            field_name="ORGANIZATION_ID",
            request=request,
            user=USER,
        )
    )


def test_create_generation_job_returns_422_for_invalid_specification(
    monkeypatch,
):
    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(
            create_job=lambda **kwargs: (_ for _ in ()).throw(
                VALIDATION_ERROR
            )
        ),
    )

    assert_validation_422(
        lambda: generation_api.create_generation_job(
            data_model_id=DATA_MODEL_ID,
            user=USER,
        )
    )


def test_start_generation_job_returns_422_for_invalid_specification(
    monkeypatch,
):
    created_job = SimpleNamespace(status=GenerationJobStatus.CREATED)

    generation_service = SimpleNamespace(
        get_job=lambda **kwargs: created_job,
        start_job=lambda **kwargs: (_ for _ in ()).throw(
            VALIDATION_ERROR
        ),
    )

    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        generation_service,
    )

    assert_validation_422(
        lambda: generation_api.start_generation_job(
            data_model_id=DATA_MODEL_ID,
            job_id="test-job",
            background_tasks=BackgroundTasks(),
            current_user=USER,
        )
    )


@pytest.mark.parametrize(
    ("previous_status", "expected_resumed"),
    [
        (GenerationJobStatus.CREATED, False),
        (GenerationJobStatus.INTERRUPTED, True),
        (GenerationJobStatus.FAILED, True),
        (GenerationJobStatus.PARTIALLY_COMPLETED, True),
    ],
)
def test_start_generation_job_records_start_and_resume_activity(
    monkeypatch,
    previous_status,
    expected_resumed,
):
    previous_job = SimpleNamespace(status=previous_status)
    started_job = SimpleNamespace(
        status=GenerationJobStatus.PREPARING,
        attempt_id="attempt-002",
        job_id="test-job",
        total_target_rows=100,
    )
    recorded_activities = []

    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(
            get_job=lambda **kwargs: previous_job,
            start_job=lambda **kwargs: started_job,
        ),
    )
    monkeypatch.setattr(
        generation_api,
        "data_model_repository",
        SimpleNamespace(
            get_by_id_any=lambda data_model_id: SimpleNamespace(
                owner_user_id="owner-user",
                name="Test Model",
            )
        ),
    )
    monkeypatch.setattr(
        generation_api,
        "activity_service",
        SimpleNamespace(
            record=lambda **kwargs: recorded_activities.append(kwargs)
        ),
    )

    background_tasks = BackgroundTasks()

    result = asyncio.run(
        generation_api.start_generation_job(
            data_model_id=DATA_MODEL_ID,
            job_id="test-job",
            background_tasks=background_tasks,
            current_user=USER,
        )
    )

    assert result is started_job
    assert len(background_tasks.tasks) == 1
    assert len(recorded_activities) == 1

    activity = recorded_activities[0]
    assert activity["owner_user_id"] == "owner-user"
    assert activity["actor_user_id"] == USER.user_id
    assert activity["activity_type"] == ActivityType.GENERATION_STARTED
    assert activity["data_model_id"] == DATA_MODEL_ID
    assert activity["job_id"] == "test-job"
    assert activity["metadata"] == {
        "status": GenerationJobStatus.PREPARING.value,
        "requested_rows": 100,
        "resumed": expected_resumed,
    }


def _hold_generation_execution_lease_in_process(
    job_directory,
    release_event,
    status_queue,
):
    from app.services.generation_execution_lease import (
        generation_execution_lease,
    )

    try:
        with generation_execution_lease(
            job_directory,
            timeout=5.0,
        ):
            status_queue.put(("acquired", None))

            if not release_event.wait(timeout=10):
                raise AssertionError(
                    "Timed out waiting to release the execution lease."
                )

        status_queue.put(("released", None))

    except BaseException as exc:
        status_queue.put(
            ("error", f"{type(exc).__name__}: {exc}")
        )
        raise


def test_start_generation_job_returns_409_when_execution_lease_is_busy(
    tmp_path,
    monkeypatch,
):
    import multiprocessing

    from app.services.generation_execution_lease import (
        generation_execution_lease,
    )

    context = multiprocessing.get_context("spawn")
    release_event = context.Event()
    status_queue = context.Queue()

    holder = context.Process(
        target=_hold_generation_execution_lease_in_process,
        args=(tmp_path, release_event, status_queue),
    )

    created_job = SimpleNamespace(
        status=GenerationJobStatus.RUNNING,
        attempt_id="existing-attempt-001",
    )
    background_tasks = BackgroundTasks()

    holder.start()

    try:
        status, detail = status_queue.get(timeout=10)
        assert status == "acquired", detail

        def attempt_start(**kwargs):
            with generation_execution_lease(
                tmp_path,
                timeout=0.0,
            ):
                raise AssertionError(
                    "Start unexpectedly acquired an already-held lease."
                )

        generation_service = SimpleNamespace(
            get_job=lambda **kwargs: created_job,
            start_job=attempt_start,
        )

        monkeypatch.setattr(
            generation_api,
            "data_model_access_service",
            SimpleNamespace(can_generate=lambda **kwargs: True),
        )
        monkeypatch.setattr(
            generation_api,
            "generation_service",
            generation_service,
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                generation_api.start_generation_job(
                    data_model_id=DATA_MODEL_ID,
                    job_id="test-job",
                    background_tasks=background_tasks,
                    current_user=USER,
                )
            )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == (
            "Generation job is already being prepared or executed. "
            "Please try again."
        )
        assert background_tasks.tasks == []
        assert created_job.status == GenerationJobStatus.RUNNING
        assert created_job.attempt_id == "existing-attempt-001"

    finally:
        release_event.set()
        holder.join(timeout=15)

        if holder.is_alive():
            holder.terminate()
            holder.join(timeout=5)

    assert not holder.is_alive(), (
        "Execution lease holder did not exit."
    )
    assert holder.exitcode == 0, (
        f"Execution lease process exited with code {holder.exitcode}."
    )

    status, detail = status_queue.get(timeout=5)
    assert status == "released", detail

    # Confirm that the OS-level lease is reusable after child exit.
    with generation_execution_lease(tmp_path, timeout=0.0):
        pass

    status_queue.close()
    status_queue.join_thread()


def configure_invalid_population_validation(monkeypatch):
    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(
            can_view=lambda **kwargs: True,
            can_edit=lambda **kwargs: True,
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_service",
        SimpleNamespace(
            get_specification=lambda **kwargs: {"entities": []},
            accept_population_plan=lambda **kwargs: pytest.fail(
                "Population plan acceptance must not be reached."
            ),
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_validation_service",
        SimpleNamespace(
            validate=lambda specification: VALIDATION_RESULT,
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "population_service",
        SimpleNamespace(
            get_population_plan=lambda **kwargs: pytest.fail(
                "Population Plan must not be reached."
            ),
            build_candidate_plan=lambda **kwargs: pytest.fail(
                "Population candidate planning must not be reached."
            ),
        ),
    )


def test_get_population_plan_returns_422_for_invalid_specification(monkeypatch):
    configure_invalid_population_validation(monkeypatch)

    assert_validation_422(
        lambda: specification_api.get_population_plan(
            data_model_id=DATA_MODEL_ID,
            user=USER,
        )
    )


def test_build_population_candidate_returns_422_for_invalid_specification(
    monkeypatch,
):
    configure_invalid_population_validation(monkeypatch)

    request = SimpleNamespace(target=100, driver=None)

    assert_validation_422(
        lambda: specification_api.build_population_candidate(
            data_model_id=DATA_MODEL_ID,
            request=request,
            user=USER,
        )
    )


def test_accept_population_plan_returns_422_for_invalid_specification(
    monkeypatch,
):
    configure_invalid_population_validation(monkeypatch)

    request = SimpleNamespace(populations={})

    assert_validation_422(
        lambda: specification_api.accept_population_plan(
            data_model_id=DATA_MODEL_ID,
            request=request,
            user=USER,
        )
    )


def test_population_plan_continues_when_specification_is_valid(monkeypatch):
    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(can_view=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_service",
        SimpleNamespace(
            get_specification=lambda **kwargs: {"entities": []},
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_validation_service",
        SimpleNamespace(
            validate=lambda specification: {"can_continue": True},
        ),
    )
    expected = {"populations": {"ORGANIZATION": 100}}
    monkeypatch.setattr(
        specification_api,
        "population_service",
        SimpleNamespace(
            get_population_plan=lambda **kwargs: expected,
        ),
    )

    response = asyncio.run(
        specification_api.get_population_plan(
            data_model_id=DATA_MODEL_ID,
            user=USER,
        )
    )

    assert response == expected


def test_generation_readiness_returns_422_for_invalid_specification(
    monkeypatch,
):
    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(
            get_readiness=lambda **kwargs: (_ for _ in ()).throw(
                VALIDATION_ERROR
            ),
        ),
    )

    assert_validation_422(
        lambda: generation_api.get_generation_readiness(
            data_model_id=DATA_MODEL_ID,
            user=USER,
        )
    )



@pytest.mark.parametrize(
    ("route_name", "service_method"),
    [
        ("pause_generation_job", "pause_job"),
        ("cancel_generation_job", "cancel_job"),
    ],
)
def test_generation_control_routes_accept_running_job(
    monkeypatch,
    route_name,
    service_method,
):
    running_job = SimpleNamespace(
        data_model_id=DATA_MODEL_ID,
        job_id="test-job",
        status=GenerationJobStatus.RUNNING,
    )
    calls = []

    def request_control(**kwargs):
        calls.append(kwargs)
        return running_job

    service = SimpleNamespace(
        **{service_method: request_control}
    )

    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        service,
    )

    result = asyncio.run(
        getattr(generation_api, route_name)(
            data_model_id=DATA_MODEL_ID,
            job_id="test-job",
            current_user=USER,
        )
    )

    assert result is running_job
    assert calls == [{
        "data_model_id": DATA_MODEL_ID,
        "job_id": "test-job",
    }]


@pytest.mark.parametrize(
    ("route_name", "service_method"),
    [
        ("pause_generation_job", "pause_job"),
        ("cancel_generation_job", "cancel_job"),
    ],
)
def test_generation_control_routes_return_404_for_missing_job(
    monkeypatch,
    route_name,
    service_method,
):
    def request_control(**kwargs):
        raise ValueError("Generation job not found.")

    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(**{service_method: request_control}),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            getattr(generation_api, route_name)(
                data_model_id=DATA_MODEL_ID,
                job_id="missing-job",
                current_user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."


@pytest.mark.parametrize(
    ("route_name", "service_method"),
    [
        ("pause_generation_job", "pause_job"),
        ("cancel_generation_job", "cancel_job"),
    ],
)
def test_generation_control_routes_return_409_for_invalid_transition(
    monkeypatch,
    route_name,
    service_method,
):
    detail = (
        "Cannot request pause for a job in COMPLETED state. "
        "Only RUNNING jobs accept controls."
    )

    def request_control(**kwargs):
        raise ValueError(detail)

    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(**{service_method: request_control}),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            getattr(generation_api, route_name)(
                data_model_id=DATA_MODEL_ID,
                job_id="test-job",
                current_user=USER,
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == detail


@pytest.mark.parametrize(
    "route_name",
    [
        "pause_generation_job",
        "cancel_generation_job",
    ],
)
def test_generation_control_routes_hide_inaccessible_data_models(
    monkeypatch,
    route_name,
):
    service_called = False

    def unexpected_call(**kwargs):
        nonlocal service_called
        service_called = True
        raise AssertionError("Service must not be called.")

    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: False),
    )
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(
            pause_job=unexpected_call,
            cancel_job=unexpected_call,
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            getattr(generation_api, route_name)(
                data_model_id=DATA_MODEL_ID,
                job_id="test-job",
                current_user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Data model not found."
    assert service_called is False
