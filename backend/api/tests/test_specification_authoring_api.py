import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import ai as ai_api
from app.api import specification as specification_api
from app.interfaces.ai_provider import AIWholeSpecificationProposal
from app.interfaces.auth_user import AuthUser
from app.models.ai_whole_specification_proposal_model import (
    AIWholeSpecificationProposalRequestModel,
)
from app.models.specification_model import SpecificationModel


def test_proposal_keeps_propose_status_when_validation_fails(monkeypatch):
    candidate = {"entities": []}
    findings = [{"severity": "ERROR", "message": "At least one entity is required."}]
    proposal = AIWholeSpecificationProposal(
        status="PROPOSE",
        message="Best-effort proposal created.",
        specification=candidate,
        assumptions=["Population was not specified."],
        clarification_questions=[],
        reasoning="Conservative best-effort interpretation.",
    )

    monkeypatch.setattr(
        ai_api,
        "_ai_service",
        SimpleNamespace(propose_whole_specification=lambda **kwargs: proposal),
    )
    monkeypatch.setattr(
        ai_api,
        "_specification_validation_service",
        SimpleNamespace(
            validate=lambda specification: {
                "can_continue": False,
                "findings": findings,
            }
        ),
    )

    response = ai_api.propose_whole_specification(
        request=AIWholeSpecificationProposalRequestModel(
            prompt="Create a product model"
        ),
        user=AuthUser(
            user_id="test-user",
            email="test@example.com",
            display_name="Test User",
        ),
    )

    assert response.status == "PROPOSE"
    assert response.specification == candidate
    assert response.validation["can_continue"] is False
    assert response.validation["findings"] == findings
    assert "needs correction" in response.message


def test_semantically_invalid_specification_can_be_saved(monkeypatch):
    candidate = SpecificationModel(
        version="1.0",
        vocabulary_version="1.0",
        model={},
        generation={},
        entities=[],
        relationships=[],
        foreign_keys=[],
        constraints=[],
        dependencies=[],
        statistical_behavior=[],
        scenarios=[],
    )
    saved_candidate = candidate.model_dump(mode="python")
    save_calls = []
    validation_calls = []

    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(can_edit=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_validation_service",
        SimpleNamespace(
            validate=lambda specification: validation_calls.append(specification)
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_service",
        SimpleNamespace(
            save_specification=lambda **kwargs: (
                save_calls.append(kwargs) or saved_candidate
            )
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "data_model_repository",
        SimpleNamespace(get_by_id_any=lambda **kwargs: None),
    )

    response = asyncio.run(
        specification_api.save_specification(
            data_model_id="test-model",
            request=candidate,
            user=AuthUser(
                user_id="test-user",
                email="test@example.com",
                display_name="Test User",
            ),
        )
    )

    assert response.version == "1.0"
    assert len(save_calls) == 1
    assert save_calls[0]["data_model_id"] == "test-model"
    assert validation_calls == []

def test_manual_save_records_population_default_assumptions(monkeypatch):
    candidate = SpecificationModel(
        version="1.0",
        vocabulary_version="1.0",
        model={},
        generation={},
        entities=[
            {
                "name": "SUPPLIER",
                "fields": [],
            },
            {
                "name": "PURCHASE_ORDER",
                "fields": [],
                "population": {
                    "count": 250,
                    "scaling": "FIXED",
                },
            },
        ],
        relationships=[],
        foreign_keys=[],
        constraints=[],
        dependencies=[],
        statistical_behavior=[],
        scenarios=[],
    )

    activity_calls = []

    def save_specification(**kwargs):
        specification = kwargs["specification"]
        from app.services.specification_defaults import (
            apply_specification_defaults,
        )

        saved, applied = apply_specification_defaults(specification)
        kwargs["default_assumptions"].extend(applied)
        return saved

    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(can_edit=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_service",
        SimpleNamespace(save_specification=save_specification),
    )
    monkeypatch.setattr(
        specification_api,
        "data_model_repository",
        SimpleNamespace(
            get_by_id_any=lambda **kwargs: SimpleNamespace(
                owner_user_id="test-user",
            )
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_import_repository",
        SimpleNamespace(revision=lambda specification: 1),
    )
    monkeypatch.setattr(
        specification_api,
        "activity_service",
        SimpleNamespace(record=lambda **kwargs: activity_calls.append(kwargs)),
    )

    response = asyncio.run(
        specification_api.save_specification(
            data_model_id="test-model",
            request=candidate,
            user=AuthUser(
                user_id="test-user",
                email="test@example.com",
                display_name="Test User",
            ),
        )
    )

    assert response.entities[0]["population"]["count"] == 100
    assert response.entities[0]["population"]["scaling"] == "SCALABLE"
    assert response.entities[1]["population"]["count"] == 250
    assert response.entities[1]["population"]["scaling"] == "FIXED"
    assert not hasattr(response, "assumptions")

    assert len(activity_calls) == 1
    metadata = activity_calls[0]["metadata"]
    assumptions = metadata["default_assumptions"]
    assert len(assumptions) == 2
    assert any("SUPPLIER" in item and "count = 100" in item for item in assumptions)
    assert any("SUPPLIER" in item and "SCALABLE" in item for item in assumptions)
