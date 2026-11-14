import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import generation as generation_api
from app.interfaces.auth_user import AuthUser
from app.models.generation_model import GenerationQualityProfile


USER = AuthUser(
    user_id="test-user",
    email="test@example.com",
    display_name="Test User",
)

DATA_MODEL_ID = "test-model"
JOB_ID = "test-job"


def make_quality():
    return GenerationQualityProfile(
        population_fidelity={
            "measurement_status": "AVAILABLE",
            "fidelity_rate": 0.95,
        },
        distribution_fidelity={
            "measurement_status": "AVAILABLE",
            "fields_analyzed": 12,
        },
        relationship_fidelity={
            "measurement_status": "AVAILABLE",
            "relationships_analyzed": 5,
        },
        identity_space_utilization={
            "measurement_status": "AVAILABLE",
            "entities_analyzed": 3,
        },
        statistical_fidelity={
            "measurement_status": "AVAILABLE",
            "numeric_fields_analyzed": 8,
        },
        performance={
            "measurement_status": "AVAILABLE",
            "rows_per_second": 125.5,
        },
        validation={
            "valid": False,
            "errors": ["This belongs to validation, not quality."],
        },
    )


def make_job(**overrides):
    values = {
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "quality": make_quality(),
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


def test_get_generation_quality_returns_six_quality_dimensions(monkeypatch):
    job = make_job()
    configure_access(monkeypatch)
    configure_job(monkeypatch, job)

    response = asyncio.run(
        generation_api.get_generation_quality(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    assert response.data_model_id == DATA_MODEL_ID
    assert response.job_id == JOB_ID
    assert response.quality is not None

    result = response.model_dump()
    quality = result["quality"]

    assert set(quality) == {
        "population_fidelity",
        "distribution_fidelity",
        "relationship_fidelity",
        "identity_space_utilization",
        "statistical_fidelity",
        "performance",
    }

    assert quality["population_fidelity"]["fidelity_rate"] == 0.95
    assert quality["distribution_fidelity"]["fields_analyzed"] == 12
    assert quality["relationship_fidelity"]["relationships_analyzed"] == 5
    assert quality["identity_space_utilization"]["entities_analyzed"] == 3
    assert quality["statistical_fidelity"]["numeric_fields_analyzed"] == 8
    assert quality["performance"]["rows_per_second"] == 125.5

    assert "validation" not in quality


def test_get_generation_quality_returns_null_when_profile_is_unavailable(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job(quality=None))

    response = asyncio.run(
        generation_api.get_generation_quality(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    assert response.quality is None


def test_get_generation_quality_returns_404_when_access_is_denied(
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
            generation_api.get_generation_quality(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Data model not found."


def test_get_generation_quality_returns_404_when_job_is_missing(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, None)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_quality(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."


def test_get_generation_quality_returns_404_for_mismatched_data_model(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(
        monkeypatch,
        make_job(data_model_id="another-model"),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_quality(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."



def test_quality_summary_returns_only_six_summary_metrics(monkeypatch):
    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job())

    response = asyncio.run(
        generation_api.get_generation_quality_summary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    result = response.model_dump()

    assert result["data_model_id"] == DATA_MODEL_ID
    assert result["job_id"] == JOB_ID
    assert set(result) == {
        "data_model_id",
        "job_id",
        "population_fidelity",
        "relationship_count",
        "distribution_count",
        "statistical_count",
        "throughput",
        "identity_count",
    }

    assert result["population_fidelity"] == {
        "value": 0.95,
        "measurement_status": "AVAILABLE",
    }
    assert result["relationship_count"] == {
        "value": 5,
        "measurement_status": "AVAILABLE",
    }
    assert result["distribution_count"] == {
        "value": 12,
        "measurement_status": "AVAILABLE",
    }
    assert result["statistical_count"] == {
        "value": 8,
        "measurement_status": "AVAILABLE",
    }
    assert result["throughput"] == {
        "value": 125.5,
        "measurement_status": "AVAILABLE",
    }
    assert result["identity_count"] == {
        "value": 3,
        "measurement_status": "AVAILABLE",
    }


def test_quality_summary_reads_persisted_dictionary_profile(monkeypatch):
    # The quality store returns dictionaries, not Pydantic objects.
    quality = make_quality().model_dump()

    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job(quality=quality))

    response = asyncio.run(
        generation_api.get_generation_quality_summary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    result = response.model_dump()

    assert result["population_fidelity"] == {
        "value": 0.95,
        "measurement_status": "AVAILABLE",
    }
    assert result["relationship_count"] == {
        "value": 5,
        "measurement_status": "AVAILABLE",
    }
    assert result["distribution_count"] == {
        "value": 12,
        "measurement_status": "AVAILABLE",
    }
    assert result["statistical_count"] == {
        "value": 8,
        "measurement_status": "AVAILABLE",
    }
    assert result["throughput"] == {
        "value": 125.5,
        "measurement_status": "AVAILABLE",
    }
    assert result["identity_count"] == {
        "value": 3,
        "measurement_status": "AVAILABLE",
    }


def test_quality_summary_returns_unavailable_metrics_without_profile(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job(quality=None))

    response = asyncio.run(
        generation_api.get_generation_quality_summary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    result = response.model_dump()

    for name in (
        "population_fidelity",
        "relationship_count",
        "distribution_count",
        "statistical_count",
        "throughput",
        "identity_count",
    ):
        assert result[name] == {
            "value": None,
            "measurement_status": "UNAVAILABLE",
        }


def test_quality_summary_preserves_failed_measurement_status(monkeypatch):
    quality = make_quality().model_copy(
        update={
            "population_fidelity": {
                "measurement_status": "FAILED",
                "error": "Internal measurement error.",
            },
            "performance": {
                "available": False,
            },
        }
    )

    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job(quality=quality))

    response = asyncio.run(
        generation_api.get_generation_quality_summary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    result = response.model_dump()

    assert result["population_fidelity"] == {
        "value": None,
        "measurement_status": "FAILED",
    }
    assert result["throughput"] == {
        "value": None,
        "measurement_status": "UNAVAILABLE",
    }


def test_quality_summary_marks_missing_metric_value_unavailable(monkeypatch):
    quality = make_quality().model_copy(
        update={
            "population_fidelity": {
                "fidelity_rate": None,
            },
        }
    )

    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job(quality=quality))

    response = asyncio.run(
        generation_api.get_generation_quality_summary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    assert response.population_fidelity.value is None
    assert response.population_fidelity.measurement_status == "UNAVAILABLE"


def test_quality_summary_returns_404_when_access_is_denied(monkeypatch):
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
            generation_api.get_generation_quality_summary(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Data model not found."


def test_quality_summary_returns_404_when_job_is_missing(monkeypatch):
    configure_access(monkeypatch)
    configure_job(monkeypatch, None)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_quality_summary(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."


def test_quality_summary_returns_404_for_mismatched_data_model(monkeypatch):
    configure_access(monkeypatch)
    configure_job(
        monkeypatch,
        make_job(data_model_id="another-model"),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_quality_summary(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."
