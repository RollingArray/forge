import logging
from types import SimpleNamespace

from app.models.generation_model import GenerationJobStatus
from app.services.generation.run_service import GenerationRunService


class FakeExecutor:
    def __init__(
        self,
        target_rows: int = 3,
        generated_rows: int = 3,
    ):
        self.target_rows = target_rows
        self.generated_rows = generated_rows

    def execute(self, **kwargs):
        entity = SimpleNamespace(
            entity_name="PRODUCT",
            target_rows=self.target_rows,
            generated_rows=self.generated_rows,
            elapsed_seconds=0.5,
            peak_memory_mb=12.0,
            vocabulary_semantic_calls=(),
            chunks=(),
        )
        return SimpleNamespace(
            generated_rows=self.generated_rows,
            target_rows=self.target_rows,
            elapsed_seconds=0.5,
            entities=(entity,),
        )


class FakeValidator:
    def __init__(
        self,
        valid: bool = True,
        expected_rows: int = 3,
        generated_rows: int = 3,
    ):
        self.valid = valid
        self.expected_rows = expected_rows
        self.generated_rows = generated_rows

    def validate(self, **kwargs):
        return SimpleNamespace(
            valid=self.valid,
            entity_count=1,
            expected_rows=self.expected_rows,
            generated_rows=self.generated_rows,
            error_count=0 if self.valid else 1,
            errors=[] if self.valid else ["Validation failed"],
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


def test_partial_generation_is_reported_when_validation_fails():
    service = GenerationRunService(
        executor=FakeExecutor(target_rows=3, generated_rows=3),
        validator=FakeValidator(
            valid=False,
            expected_rows=3,
            generated_rows=3,
        ),
        quality_service=FailingQualityService(),
    )

    result = service.run(
        specification={
            "generation": {"seed": 42, "scenario": "NORMAL"},
            "entities": [],
        },
        plan=SimpleNamespace(),
        data_model_id="model-1",
        job_id="job-partial",
    )

    assert result.status == GenerationJobStatus.PARTIALLY_COMPLETED
    assert result.requested_rows == 3
    assert result.generated_rows == 3
    assert result.validation.valid is False
    assert result.validation.error_count == 1



def test_generation_with_zero_rows_is_reported_as_failed():
    service = GenerationRunService(
        executor=FakeExecutor(target_rows=3, generated_rows=0),
        validator=FakeValidator(
            valid=False,
            expected_rows=3,
            generated_rows=0,
        ),
        quality_service=FailingQualityService(),
    )

    result = service.run(
        specification={
            "generation": {"seed": 42, "scenario": "NORMAL"},
            "entities": [],
        },
        plan=SimpleNamespace(),
        data_model_id="model-1",
        job_id="job-failed",
    )

    assert result.status == GenerationJobStatus.FAILED
    assert result.requested_rows == 3
    assert result.generated_rows == 0
    assert result.validation.valid is False
