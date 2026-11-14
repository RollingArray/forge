from __future__ import annotations

import pytest

from app.services.generation.quality import GenerationQualityService
from app.services.generation_planner import (
    GenerationEntityPlan,
    GenerationPlan,
)


class FakeArtifactReader:
    def __init__(self, rows_by_entity: dict[str, list[dict[str, str]]]):
        self.rows_by_entity = rows_by_entity

    def iter_entity_chunks(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ):
        yield from self.rows_by_entity.get(entity_name, [])


@pytest.mark.parametrize(
    ("requested_rows", "generated_rows", "expected_fidelity"),
    [
        (0, 0, None),
        (0, 2, None),
        (10, 10, 1.0),
        (10, 7, 0.7),
        (10, 13, 0.7),
    ],
)
def test_population_fidelity_uses_row_count_agreement(
    requested_rows: int,
    generated_rows: int,
    expected_fidelity: float | None,
) -> None:
    reader = FakeArtifactReader(
        {
            "ITEM": [
                {"ID": str(index)}
                for index in range(generated_rows)
            ],
        }
    )
    service = GenerationQualityService(artifact_reader=reader)
    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="ITEM",
                target_rows=requested_rows,
            ),
        )
    )

    result = service.analyze_population_fidelity(
        specification={"entities": [{"name": "ITEM"}]},
        plan=plan,
        data_model_id="model-1",
        job_id="job-1",
    )

    entity_fidelity = result["entities"]["ITEM"]["fidelity_rate"]

    assert entity_fidelity == pytest.approx(expected_fidelity)
    assert result["fidelity_rate"] == pytest.approx(expected_fidelity)
    assert entity_fidelity == result["fidelity_rate"]


def _analyze_distribution(
    rows: list[dict[str, str | None]],
    configured_values: object,
) -> dict:
    reader = FakeArtifactReader({"ITEM": rows})
    service = GenerationQualityService(artifact_reader=reader)

    return service.analyze_distribution_fidelity(
        specification={
            "entities": [
                {
                    "name": "ITEM",
                    "fields": [
                        {
                            "name": "CATEGORY",
                            "generation": {
                                "distribution": "CATEGORICAL",
                                "parameters": {
                                    "values": configured_values,
                                },
                            },
                        }
                    ],
                }
            ]
        },
        data_model_id="model-1",
        job_id="job-1",
    )


def test_distribution_reports_unavailable_measurement() -> None:
    result = _analyze_distribution([], ["A", "B"])
    field = result["fields"]["ITEM.CATEGORY"]

    assert field["measurement_status"] == "UNAVAILABLE"
    assert field["rows_total"] == 0
    assert field["rows_observed"] == 0
    assert field["category_coverage"] is None
    assert field["maximum_absolute_probability_difference"] is None


def test_distribution_distinguishes_measured_all_missing_values() -> None:
    result = _analyze_distribution(
        [{"CATEGORY": None}, {"CATEGORY": ""}],
        ["A", "B"],
    )
    field = result["fields"]["ITEM.CATEGORY"]

    assert field["measurement_status"] == "AVAILABLE"
    assert field["rows_total"] == 2
    assert field["rows_observed"] == 0
    assert field["missing_count"] == 2
    assert field["category_coverage"] == 0.0
    assert field["maximum_absolute_probability_difference"] is None


def test_distribution_exposes_unexpected_categories() -> None:
    result = _analyze_distribution(
        [
            {"CATEGORY": "A"},
            {"CATEGORY": "C"},
            {"CATEGORY": "C"},
        ],
        ["A", "B"],
    )
    field = result["fields"]["ITEM.CATEGORY"]

    assert field["measurement_status"] == "AVAILABLE"
    assert field["unexpected_category_count"] == 1
    assert field["unexpected_categories"] == {"C": 2}


@pytest.mark.parametrize("configured_values", [[], None, "A"])
def test_distribution_reports_invalid_configuration(
    configured_values: object,
) -> None:
    result = _analyze_distribution([], configured_values)

    assert result["fields_analyzed"] == 1
    field = result["fields"]["ITEM.CATEGORY"]
    assert field["measurement_status"] == "INVALID_CONFIGURATION"

@pytest.mark.parametrize(
    ("dimension", "method_name"),
    [
        ("population_fidelity", "analyze_population_fidelity"),
        ("distribution_fidelity", "analyze_distribution_fidelity"),
        ("relationship_fidelity", "analyze_relationship_fidelity"),
        ("identity_space_utilization", "analyze_identity_space_utilization"),
        ("statistical_fidelity", "analyze_statistical_fidelity"),
        ("performance", "analyze_performance"),
    ],
)
def test_quality_profile_isolates_dimension_failures(
    dimension: str,
    method_name: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging
    from types import SimpleNamespace

    service = GenerationQualityService(
        artifact_reader=FakeArtifactReader({}),
    )

    def successful_measurement(**kwargs: object) -> dict:
        return {"measurement_status": "AVAILABLE", "verified": True}

    def failing_measurement(**kwargs: object) -> dict:
        raise RuntimeError("simulated analyzer failure")

    method_names = [
        "analyze_population_fidelity",
        "analyze_distribution_fidelity",
        "analyze_relationship_fidelity",
        "analyze_identity_space_utilization",
        "analyze_statistical_fidelity",
        "analyze_performance",
    ]

    for name in method_names:
        monkeypatch.setattr(service, name, successful_measurement)

    monkeypatch.setattr(service, method_name, failing_measurement)

    validation = {"valid": True, "evidence": {"checked": True}}

    with caplog.at_level(logging.ERROR):
        result = service.build_quality_profile(
            specification={"entities": []},
            plan=SimpleNamespace(),
            data_model_id="model-1",
            job_id="job-1",
            total_generated_rows=3,
            elapsed_seconds=0.5,
            validation=validation,
        )

    assert result[dimension] == {
        "measurement_status": "FAILED",
        "error": "Quality measurement failed.",
    }

    dimension_names = [
        "population_fidelity",
        "distribution_fidelity",
        "relationship_fidelity",
        "identity_space_utilization",
        "statistical_fidelity",
        "performance",
    ]

    for other_dimension in dimension_names:
        if other_dimension == dimension:
            continue
        assert result[other_dimension]["measurement_status"] == "AVAILABLE"
        assert result[other_dimension]["verified"] is True

    assert result["validation"] is validation
    assert f"Quality dimension {dimension} failed for job job-1" in caplog.text
    assert "simulated analyzer failure" not in result[dimension]["error"]
