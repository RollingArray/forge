import asyncio
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api import generation as generation_api
from app.api import specification as specification_api
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

