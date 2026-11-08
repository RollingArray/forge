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
