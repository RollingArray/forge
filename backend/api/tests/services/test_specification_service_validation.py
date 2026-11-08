from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models.specification_field_model import (
    CreateFieldRequest,
    UpdateFieldRequest,
)
from app.services.specification_service import SpecificationService
from app.services.specification_validation_error import (
    SpecificationValidationError,
)


DATA_MODEL_ID = "MODEL-TEST"
ACTOR_USER_ID = "USER-TEST"
ENTITY_NAME = "ORGANIZATION"


class FakeSpecificationRepository:
    def __init__(self, specification):
        self.specification = deepcopy(specification)
        self.saved = []

    @contextmanager
    def transaction(self, data_model_id):
        yield

    def get_or_create(self, **kwargs):
        return deepcopy(self.specification)

    def save(self, *, data_model_id, specification):
        saved_specification = deepcopy(specification)
        self.saved.append(saved_specification)
        self.specification = deepcopy(saved_specification)
        return deepcopy(saved_specification)


class FakeDataModelRepository:
    def get_by_id_any(self, *, data_model_id):
        return SimpleNamespace(
            name="Test Model",
            description="Specification service test",
            owner_user_id=ACTOR_USER_ID,
        )


class FakeValidationService:
    def validate(self, specification):
        field_names = {
            field.get("name")
            for entity in specification.get("entities", [])
            for field in entity.get("fields", [])
        }

        valid = "INVALID_FIELD" not in field_names

        return {
            "can_continue": valid,
            "errors": 0 if valid else 1,
            "warnings": 0,
            "findings": [],
        }


def build_service():
    specification = {
        "name": "Test Model",
        "version": "1.0",
        "entities": [
            {
                "name": ENTITY_NAME,
                "fields": [
                    {
                        "name": "ORGANIZATION_ID",
                        "type": "IDENTIFIER",
                    }
                ],
            }
        ],
    }

    repository = FakeSpecificationRepository(specification)
    activity_service = MagicMock()

    service = SpecificationService(
        data_model_repository=FakeDataModelRepository(),
        specification_repository=repository,
        activity_service=activity_service,
        specification_validation_service=FakeValidationService(),
    )

    return service, repository, specification


def test_create_field_rejects_invalid_candidate_without_persisting():
    service, repository, original = build_service()

    request = CreateFieldRequest.model_validate({
        "name": "INVALID_FIELD",
        "type": "STRING",
    })

    with pytest.raises(SpecificationValidationError):
        service.create_field(
            data_model_id=DATA_MODEL_ID,
            actor_user_id=ACTOR_USER_ID,
            entity_name=ENTITY_NAME,
            request=request,
        )

    assert repository.saved == []
    assert repository.specification == original


def test_create_field_persists_valid_candidate():
    service, repository, _ = build_service()

    request = CreateFieldRequest.model_validate({
        "name": "DESCRIPTION",
        "type": "STRING",
    })

    result = service.create_field(
        data_model_id=DATA_MODEL_ID,
        actor_user_id=ACTOR_USER_ID,
        entity_name=ENTITY_NAME,
        request=request,
    )

    assert result["name"] == "DESCRIPTION"
    assert len(repository.saved) == 1

    saved_fields = repository.saved[0]["entities"][0]["fields"]
    assert any(field["name"] == "DESCRIPTION" for field in saved_fields)


def test_update_field_rejects_invalid_candidate_without_persisting():
    service, repository, original = build_service()

    request = UpdateFieldRequest.model_validate({
        "name": "INVALID_FIELD",
    })

    with pytest.raises(SpecificationValidationError):
        service.update_field(
            data_model_id=DATA_MODEL_ID,
            actor_user_id=ACTOR_USER_ID,
            entity_name=ENTITY_NAME,
            field_name="ORGANIZATION_ID",
            request=request,
        )

    assert repository.saved == []
    assert repository.specification == original


def test_update_field_persists_valid_candidate():
    service, repository, _ = build_service()

    request = UpdateFieldRequest.model_validate({
        "name": "ORG_ID",
    })

    result = service.update_field(
        data_model_id=DATA_MODEL_ID,
        actor_user_id=ACTOR_USER_ID,
        entity_name=ENTITY_NAME,
        field_name="ORGANIZATION_ID",
        request=request,
    )

    assert result["name"] == "ORG_ID"
    assert len(repository.saved) == 1

    saved_fields = repository.saved[0]["entities"][0]["fields"]
    assert any(field["name"] == "ORG_ID" for field in saved_fields)
    assert not any(
        field["name"] == "ORGANIZATION_ID"
        for field in saved_fields
    )

def test_save_specification_applies_population_defaults_and_reports_assumptions():
    service, repository, _ = build_service()

    specification = {
        "name": "Test Model",
        "version": "1.0",
        "entities": [
            {"name": "SUPPLIER", "fields": []},
            {
                "name": "PURCHASE_ORDER",
                "fields": [],
                "population": {"count": 250, "scaling": "FIXED"},
            },
        ],
    }
    original = deepcopy(specification)
    assumptions = []

    result = service.save_specification(
        data_model_id=DATA_MODEL_ID,
        specification=specification,
        default_assumptions=assumptions,
    )

    assert result is not None
    assert result["entities"][0]["population"] == {
        "count": 100,
        "scaling": "SCALABLE",
    }
    assert result["entities"][1]["population"] == {
        "count": 250,
        "scaling": "FIXED",
    }
    assert len(assumptions) == 2
    assert any(
        "SUPPLIER" in item and "count = 100" in item
        for item in assumptions
    )
    assert any(
        "SUPPLIER" in item and "SCALABLE" in item
        for item in assumptions
    )
    assert specification == original
    assert repository.saved[-1] == result


def test_save_specification_preserves_explicit_zero_population():
    service, repository, _ = build_service()

    specification = {
        "entities": [
            {
                "name": "SUPPLIER",
                "fields": [],
                "population": {"count": 0, "scaling": "FIXED"},
            }
        ]
    }
    assumptions = []

    result = service.save_specification(
        data_model_id=DATA_MODEL_ID,
        specification=specification,
        default_assumptions=assumptions,
    )

    assert result["entities"][0]["population"] == {
        "count": 0,
        "scaling": "FIXED",
    }
    assert assumptions == []
    assert len(repository.saved) == 1


def test_save_specification_remains_compatible_without_assumptions_output():
    service, repository, _ = build_service()

    result = service.save_specification(
        data_model_id=DATA_MODEL_ID,
        specification={
            "entities": [{"name": "SUPPLIER", "fields": []}]
        },
    )

    assert result["entities"][0]["population"]["count"] == 100
    assert len(repository.saved) == 1

