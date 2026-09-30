from dataclasses import dataclass
from typing import Any

from app.services.generation.executor import GenerationExecutor
from app.services.generation_planner import (
    GenerationEntityPlan,
    GenerationPlan,
)


@dataclass
class FakeAIService:
    values: list[str]

    def generate_semantic_values(
        self,
        *,
        description: str,
        mode: str,
        count: int,
    ) -> list[str]:
        assert description == "Realistic aerospace product name."
        assert mode == "UNIQUE"
        assert count == 3

        return self.values


class FakeSemanticStore:
    def __init__(self) -> None:
        self.saved: list[dict[str, Any]] = []

    def save(
        self,
        *,
        job_id: str,
        entity_name: str,
        field_name: str,
        mode: str,
        values: list[str],
    ) -> None:
        self.saved.append(
            {
                "job_id": job_id,
                "entity_name": entity_name,
                "field_name": field_name,
                "mode": mode,
                "values": list(values),
            }
        )


def test_executor_persists_ai_generated_semantic_values(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    semantic_values = [
        "Hydraulic Pump",
        "Flight Control Computer",
        "Landing Gear Assembly",
    ]

    ai_service = FakeAIService(
        values=semantic_values,
    )

    semantic_store = FakeSemanticStore()

    executor = GenerationExecutor(
        seed=42,
        ai_service=ai_service,
        semantic_store=semantic_store,
    )

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {
                    "count": 3,
                },
                "fields": [
                    {
                        "name": "PRODUCT_NAME",
                        "type": "STRING",
                        "generation": {
                            "generator": "SEMANTIC",
                            "parameters": {
                                "description": (
                                    "Realistic aerospace product name."
                                ),
                                "mode": "UNIQUE",
                            },
                        },
                    },
                ],
            },
        ],
        "foreign_keys": [],
    }

    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="PRODUCT",
                target_rows=3,
            ),
        ),
    )

    executor.execute(
        specification=specification,
        plan=plan,
        job_id="FORGE-TEST",
    )

    assert semantic_store.saved == [
        {
            "job_id": "FORGE-TEST",
            "entity_name": "PRODUCT",
            "field_name": "PRODUCT_NAME",
            "mode": "UNIQUE",
            "values": semantic_values,
        },
    ]


class FakeCheckpointStore:
    def __init__(self, checkpoint=None) -> None:
        self.checkpoint = checkpoint

    def get(self, job_id: str):
        return self.checkpoint


def test_executor_detects_existing_checkpoint() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(
            checkpoint={
                "job_id": "FORGE-TEST",
                "entities": {},
            },
        ),
    )

    assert executor.has_existing_checkpoint(
        "FORGE-TEST",
    )


def test_executor_detects_missing_checkpoint() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(),
    )

    assert not executor.has_existing_checkpoint(
        "FORGE-TEST",
    )
