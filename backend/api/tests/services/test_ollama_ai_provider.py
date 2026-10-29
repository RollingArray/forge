import json

import pytest

from app.services.ollama_ai_provider import OllamaAIProvider


def _provider(monkeypatch, responses):
    class FakeResponse:
        def __init__(self, content):
            self.content = content.encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return self.content

    calls = []

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data.decode()))
        return FakeResponse(
            json.dumps(
                {
                    "message": {
                        "content": json.dumps(
                            {"values": responses.pop(0)}
                        )
                    }
                }
            )
        )

    monkeypatch.setattr(
        "app.services.ollama_ai_provider.urlopen",
        fake_urlopen,
    )

    from app.services.ollama_ai_provider import AIConfiguration

    return OllamaAIProvider(
        AIConfiguration(
            provider="ollama",
            base_url="http://localhost:11434",
            model="gpt-oss:20b",
            capability_timeout_seconds=2.0,
            generation_timeout_seconds=180.0,
        )
    ), calls


def test_semantic_generation_trims_excess_values(monkeypatch):
    values = [f"Product {i}" for i in range(53)]

    provider, calls = _provider(monkeypatch, [values])

    result = provider.generate_semantic_values(
        description="Realistic aerospace product name.",
        mode="UNIQUE",
        count=50,
    )

    assert len(result) == 50
    assert result == values[:50]
    assert len(calls) == 1


def test_semantic_generation_refills_missing_values(monkeypatch):
    first = [f"Product {i}" for i in range(49)]
    refill = ["Product 49"]

    provider, calls = _provider(monkeypatch, [first, refill])

    result = provider.generate_semantic_values(
        description="Realistic aerospace product name.",
        mode="UNIQUE",
        count=50,
    )

    assert len(result) == 50
    assert result == [*first, *refill]
    assert len(calls) == 2
    assert "Count: 1" in calls[1]["messages"][1]["content"]


def _refinement_provider(monkeypatch, refinement_response):
    class FakeResponse:
        def __init__(self, content):
            self.content = content.encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return self.content

    calls = []

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data.decode()))
        return FakeResponse(
            json.dumps(
                {
                    "message": {
                        "content": json.dumps(refinement_response),
                    }
                }
            )
        )

    monkeypatch.setattr(
        "app.services.ollama_ai_provider.urlopen",
        fake_urlopen,
    )

    from app.services.ollama_ai_provider import AIConfiguration

    provider = OllamaAIProvider(
        AIConfiguration(
            provider="ollama",
            base_url="http://localhost:11434",
            model="gpt-oss:20b",
            capability_timeout_seconds=2.0,
            generation_timeout_seconds=180.0,
        )
    )
    return provider, calls


def _valid_refinement_response(question):
    return {
        "refined_prompt": "Generate realistic aerospace products.",
        "completeness_status": "NEEDS_REVIEW",
        "summary": "The domain is understood but needs clarification.",
        "understood_requirements": ["Aerospace products"],
        "assumptions": [],
        "open_questions": [question],
        "missing_requirements": ["Product quantity"],
    }


def test_prompt_refinement_preserves_recommendation_and_rationale(monkeypatch):
    provider, calls = _refinement_provider(
        monkeypatch,
        _valid_refinement_response(
            {
                "id": "product-quantity",
                "question": "How many products are required?",
        "answer_type": "integer",
        "options": [],
                "answer_type": "integer",
                "options": [],
                "suggested_answer": "Generate 1000 products.",
                "recommendation_rationale": (
                    "A starting population helps evaluate the initial model."
                ),
                "required": True,
            }
        ),
    )

    result = provider.refine_specification_prompt(
        "Generate aerospace product data."
    )

    question = result.open_questions[0]
    assert question.suggested_answer == "Generate 1000 products."
    assert question.recommendation_rationale == (
        "A starting population helps evaluate the initial model."
    )
    assert question.required is True

    question_schema = calls[0]["format"]["properties"]["open_questions"]["items"]
    assert "recommendation_rationale" in question_schema["properties"]
    assert "recommendation_rationale" in question_schema["required"]


def test_prompt_refinement_allows_missing_recommendation(monkeypatch):
    provider, _ = _refinement_provider(
        monkeypatch,
        _valid_refinement_response(
            {
                "id": "product-quantity",
                "question": "How many products are required?",
        "answer_type": "integer",
        "options": [],
                "answer_type": "integer",
                "options": [],
                "suggested_answer": None,
                "recommendation_rationale": None,
                "required": True,
            }
        ),
    )

    result = provider.refine_specification_prompt(
        "Generate aerospace product data."
    )

    question = result.open_questions[0]
    assert question.suggested_answer is None
    assert question.recommendation_rationale is None


@pytest.mark.parametrize(
    ("field", "invalid_value", "error_message"),
    [
        (
            "suggested_answer",
            1000,
            "invalid suggested answer",
        ),
        (
            "recommendation_rationale",
            {"reason": "not a string"},
            "invalid recommendation rationale",
        ),
    ],
)
def test_prompt_refinement_rejects_invalid_recommendation_fields(
    monkeypatch,
    field,
    invalid_value,
    error_message,
):
    question = {
        "id": "product-quantity",
        "question": "How many products are required?",
        "answer_type": "integer",
        "options": [],
        "suggested_answer": "Generate 1000 products.",
        "recommendation_rationale": "A starting point for testing.",
        "required": True,
    }
    question[field] = invalid_value

    provider, _ = _refinement_provider(
        monkeypatch,
        _valid_refinement_response(question),
    )

    with pytest.raises(RuntimeError, match=error_message):
        provider.refine_specification_prompt(
            "Generate aerospace product data."
        )
def _whole_specification_response(specification):
    return {
        "message": "Specification proposal prepared.",
        "specification": specification,
        "assumptions": [],
        "reasoning": "Mapped the supplied requirements to the canonical model.",
    }


def _valid_whole_specification(population_count=None):
    entity = {
        "name": "PRODUCT",
        "description": "Product records",
        "fields": [
            {
                "name": "PRODUCT_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            }
        ],
        "identity": {"fields": ["PRODUCT_ID"]},
        "population": (
            {"count": population_count, "scaling": "SCALABLE"}
            if population_count is not None
            else {"scaling": "SCALABLE"}
        ),
    }
    return {
        "version": "1.0",
        "vocabulary_version": "1.0",
        "model": {"name": "PRODUCT_MODEL", "description": "Product model"},
        "generation": {"seed": 42, "scenario": "NORMAL"},
        "entities": [entity],
        "relationships": [],
        "foreign_keys": [],
        "constraints": [],
        "dependencies": [],
        "statistical_behavior": [],
        "scenarios": [],
    }


def _whole_specification_provider(monkeypatch, responses):
    class FakeResponse:
        def __init__(self, content):
            self.content = content.encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return self.content

    calls = []

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data.decode()))
        response = responses.pop(0)
        return FakeResponse(
            json.dumps(
                {"message": {"content": json.dumps(response)}}
            )
        )

    monkeypatch.setattr(
        "app.services.ollama_ai_provider.urlopen",
        fake_urlopen,
    )

    from app.services.ollama_ai_provider import AIConfiguration

    provider = OllamaAIProvider(
        AIConfiguration(
            provider="ollama",
            base_url="http://localhost:11434",
            model="gpt-oss:20b",
            capability_timeout_seconds=2.0,
            generation_timeout_seconds=180.0,
        )
    )
    return provider, calls


def test_whole_specification_validates_without_population(
    monkeypatch,
):
    specification = _valid_whole_specification()
    provider, calls = _whole_specification_provider(
        monkeypatch,
        [_whole_specification_response(specification)],
    )

    validation_calls = []
    planning_calls = []

    from app.services.generation_planner import GenerationPlanner

    monkeypatch.setattr(
        GenerationPlanner,
        "validate_generation_configuration",
        lambda self, value: validation_calls.append(value),
    )
    monkeypatch.setattr(
        GenerationPlanner,
        "build",
        lambda self, value: planning_calls.append(value),
    )

    result = provider.propose_whole_specification(
        prompt="Create a product model.",
        canonical_version="1.0",
        vocabulary_version="1.0",
    )

    assert result.status == "PROPOSE"
    assert len(calls) == 1
    assert validation_calls == []
    assert planning_calls == []


def test_whole_specification_does_not_retry_invalid_configuration(
    monkeypatch,
):
    invalid_specification = _valid_whole_specification()
    invalid_specification["entities"][0]["fields"][0]["identity"] = {
        "strategy": "UNSUPPORTED_STRATEGY"
    }

    provider, calls = _whole_specification_provider(
        monkeypatch,
        [_whole_specification_response(invalid_specification)],
    )

    from app.services.generation_planner import (
        GenerationPlanner,
        GenerationPlanningError,
    )

    validation_calls = []

    def validate(self, value):
        validation_calls.append(value)
        raise GenerationPlanningError(
            "Invalid generation configuration for "
            "PRODUCT.PRODUCT_ID: IDENTIFIER requires SEQUENTIAL_ID."
        )

    monkeypatch.setattr(
        GenerationPlanner,
        "validate_generation_configuration",
        validate,
    )
    monkeypatch.setattr(
        GenerationPlanner,
        "build",
        lambda self, value: pytest.fail(
            "Full planning must not run when validation fails."
        ),
    )

    result = provider.propose_whole_specification(
        prompt="Create a product model.",
        canonical_version="1.0",
        vocabulary_version="1.0",
    )

    assert result.status == "PROPOSE"
    assert result.specification == invalid_specification
    assert len(calls) == 1
    assert len(validation_calls) == 0
    assert calls[0]["options"] == {
        "temperature": 0,
        "top_p": 1,
        "seed": 42,
    }
    assert "status" not in calls[0]["format"]["properties"]
    assert "clarification_questions" not in calls[0]["format"]["properties"]


def test_whole_specification_runs_full_planning_with_population(
    monkeypatch,
):
    specification = _valid_whole_specification(population_count=100)
    provider, _ = _whole_specification_provider(
        monkeypatch,
        [_whole_specification_response(specification)],
    )

    validation_calls = []
    planning_calls = []

    from app.services.generation_planner import GenerationPlanner

    monkeypatch.setattr(
        GenerationPlanner,
        "validate_generation_configuration",
        lambda self, value: validation_calls.append(value),
    )
    monkeypatch.setattr(
        GenerationPlanner,
        "build",
        lambda self, value: planning_calls.append(value),
    )

    result = provider.propose_whole_specification(
        prompt="Create 100 product records.",
        canonical_version="1.0",
        vocabulary_version="1.0",
    )

    assert result.status == "PROPOSE"
    assert validation_calls == []
    assert planning_calls == []


def test_real_generation_configuration_validation_rejects_invalid_field_without_population():
    from app.services.generation_planner import (
        GenerationPlanner,
        GenerationPlanningError,
    )

    specification = _valid_whole_specification()
    specification["entities"][0]["fields"][0]["identity"] = {
        "strategy": "UNSUPPORTED_STRATEGY"
    }

    with pytest.raises(
        GenerationPlanningError,
        match="IDENTIFIER requires SEQUENTIAL_ID",
    ):
        GenerationPlanner().validate_generation_configuration(specification)
