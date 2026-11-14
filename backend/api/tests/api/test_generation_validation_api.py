import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import generation as generation_api
from app.interfaces.auth_user import AuthUser
from app.models.generation_model import GenerationValidationSummary


USER = AuthUser(
    user_id="test-user",
    email="test@example.com",
    display_name="Test User",
)

DATA_MODEL_ID = "test-model"
JOB_ID = "test-job"


def make_validation():
    return GenerationValidationSummary(
        valid=False,
        entity_count=2,
        expected_rows=100,
        generated_rows=95,
        error_count=1,
        errors=["Five rows were not generated."],
        warnings=["One entity has incomplete coverage."],
        evidence={
            "schema": {"status": "passed"},
            "rule_results": [
                {
                    "rule_id": "RULE-001",
                    "category": "completeness",
                    "status": "failed",
                }
            ],
        },
    )


def make_job(**overrides):
    values = {
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "validation": make_validation(),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def configure_access(monkeypatch, allowed=True):
    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: allowed),
    )


def configure_job(monkeypatch, job):
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(get_job=lambda **kwargs: job),
    )


def test_get_generation_validation_returns_validation_projection(monkeypatch):
    job = make_job()
    configure_access(monkeypatch)
    configure_job(monkeypatch, job)

    response = asyncio.run(
        generation_api.get_generation_validation(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    assert response.data_model_id == DATA_MODEL_ID
    assert response.job_id == JOB_ID
    assert response.validation is not None
    assert response.validation.valid is False
    assert response.validation.entity_count == 2
    assert response.validation.expected_rows == 100
    assert response.validation.generated_rows == 95
    assert response.validation.error_count == 1
    assert response.validation.errors == [
        "Five rows were not generated."
    ]
    assert response.validation.warnings == [
        "One entity has incomplete coverage."
    ]
    assert response.validation.evidence == job.validation.evidence

    result = response.model_dump()
    assert set(result) == {"data_model_id", "job_id", "validation"}


def test_get_generation_validation_returns_null_when_report_is_unavailable(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job(validation=None))

    response = asyncio.run(
        generation_api.get_generation_validation(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    assert response.data_model_id == DATA_MODEL_ID
    assert response.job_id == JOB_ID
    assert response.validation is None


def test_get_generation_validation_returns_404_when_access_is_denied(
    monkeypatch,
):
    configure_access(monkeypatch, allowed=False)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(
            get_job=lambda **kwargs: pytest.fail(
                "Job lookup must not occur when access is denied."
            )
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_validation(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Data model not found."


def test_get_generation_validation_returns_404_when_job_is_missing(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, None)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_validation(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."


def test_get_generation_validation_returns_404_for_mismatched_data_model(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(
        monkeypatch,
        make_job(data_model_id="another-model"),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_validation(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."


def test_get_generation_validation_summary_returns_six_metrics(monkeypatch):
    validation = make_validation()
    validation.evidence = {
        "foreign_keys": {"relationships_checked": 19},
        "constraints": {"constraints_checked": 12},
    }
    validation.generated_rows = 7000
    validation.entity_count = 17
    validation.valid = True
    validation.error_count = 0
    validation.warnings = []

    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job(validation=validation))

    response = asyncio.run(
        generation_api.get_generation_validation_summary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    assert response.model_dump() == {
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "valid": True,
        "rows_validated": 7000,
        "expected_rows": 100,
        "entities_checked": 17,
        "relationships_checked": 19,
        "constraints_checked": 12,
        "error_count": 0,
        "warning_count": 0,
    }


def test_get_generation_validation_summary_uses_zero_for_missing_evidence(
    monkeypatch,
):
    validation = make_validation()
    validation.evidence = {}

    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job(validation=validation))

    response = asyncio.run(
        generation_api.get_generation_validation_summary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    assert response.relationships_checked == 0
    assert response.constraints_checked == 0
    assert response.warning_count == 1


def test_get_generation_validation_summary_handles_missing_validation(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job(validation=None))

    response = asyncio.run(
        generation_api.get_generation_validation_summary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    assert response.valid is None
    assert response.rows_validated == 0
    assert response.entities_checked == 0
    assert response.relationships_checked == 0
    assert response.constraints_checked == 0
    assert response.error_count == 0
    assert response.warning_count == 0


def test_get_generation_validation_summary_returns_404_when_access_is_denied(
    monkeypatch,
):
    configure_access(monkeypatch, allowed=False)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(
            get_job=lambda **kwargs: pytest.fail(
                "Job lookup must not occur when access is denied."
            )
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_validation_summary(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Data model not found."


def test_get_generation_validation_summary_returns_404_when_job_is_missing(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, None)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_validation_summary(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."


def test_get_generation_validation_summary_rejects_mismatched_data_model(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(
        monkeypatch,
        make_job(data_model_id="another-model"),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_validation_summary(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."
