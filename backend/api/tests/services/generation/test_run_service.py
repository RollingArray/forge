import logging
from types import SimpleNamespace

from app.models.generation_model import GenerationJobStatus
from app.services.generation.run_service import GenerationRunService


class FakeExecutor:
    def execute(self, **kwargs):
        entity = SimpleNamespace(
            entity_name="PRODUCT",
            target_rows=3,
            generated_rows=3,
            elapsed_seconds=0.5,
            peak_memory_mb=12.0,
            vocabulary_semantic_calls=(),
            chunks=(),
        )
        return SimpleNamespace(
            generated_rows=3,
            target_rows=3,
            elapsed_seconds=0.5,
            entities=(entity,),
        )


class FakeValidator:
    def validate(self, **kwargs):
        return SimpleNamespace(
            valid=True,
            entity_count=1,
            expected_rows=3,
            generated_rows=3,
            error_count=0,
            errors=[],
            warnings=[],
            evidence=SimpleNamespace(
                to_dict=lambda: {"checked": True},
            ),
        )


class FailingQualityService:
    def build_quality_profile(self, **kwargs):
        raise RuntimeError("Quality analysis unavailable")


def test_quality_failure_preserves_completed_generation_and_validation(
    caplog,
):
    service = GenerationRunService(
        executor=FakeExecutor(),
        validator=FakeValidator(),
        quality_service=FailingQualityService(),
    )

    with caplog.at_level(logging.ERROR):
        result = service.run(
            specification={
                "generation": {"seed": 42, "scenario": "NORMAL"},
                "entities": [],
            },
            plan=SimpleNamespace(),
            data_model_id="model-1",
            job_id="job-1",
        )

    assert result.status == GenerationJobStatus.COMPLETED
    assert result.requested_rows == 3
    assert result.generated_rows == 3
    assert result.validation.valid is True
    assert result.validation.evidence == {"checked": True}
    assert result.quality is None

    assert "Quality profile generation failed for job job-1" in caplog.text
    assert "Quality analysis unavailable" in caplog.text
