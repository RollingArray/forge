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


def test_invalid_specification_is_not_saved(monkeypatch):
    findings = [{"severity": "ERROR", "message": "Invalid entity definition."}]
    save_calls = []

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

    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(can_edit=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_validation_service",
        SimpleNamespace(
            validate=lambda specification: {
                "can_continue": False,
                "findings": findings,
            }
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_service",
        SimpleNamespace(
            save_specification=lambda **kwargs: save_calls.append(kwargs)
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
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

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["findings"] == findings
    assert save_calls == []
