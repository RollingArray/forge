from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.generation_model import (
    GenerationJobRecord,
    GenerationJobResponse,
    GenerationJobStatus,
    GenerationPreparationPhase,
    GenerationResumeIntent,
)
from app.services import generation_file_persistence
from app.services.generation_job_store import GenerationJobStore
from app.services.generation_persistence_errors import (
    JobRecordCorruptError,
    JobRecordValidationError,
    PersistenceOperationError,
)


def _job(
    job_id: str,
    status: GenerationJobStatus = GenerationJobStatus.CREATED,
    total_generated_rows: int = 0,
    attempt_id: str | None = None,
) -> GenerationJobRecord:
    return GenerationJobRecord(
        data_model_id="MODEL-TEST",
        job_id=job_id,
        status=status,
        created_at=datetime.now(timezone.utc),
        total_target_rows=100,
        total_generated_rows=total_generated_rows,
        attempt_id=attempt_id,
    )


def _store(tmp_path: Path, monkeypatch) -> GenerationJobStore:
    store = GenerationJobStore()
    monkeypatch.setattr(store, "_root", tmp_path)
    return store


def test_job_store_saves_and_reloads_job(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    job = _job("JOB-001")

    store.save(job)

    loaded = store.get("MODEL-TEST", "JOB-001")

    assert loaded is not None
    assert loaded.job_id == job.job_id
    assert loaded.status == job.status
    assert loaded.total_target_rows == 100


def test_job_store_lists_jobs_for_data_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    store.save(_job("JOB-001"))
    store.save(_job("JOB-002"))

    jobs = store.list_for_data_model("MODEL-TEST")

    assert {job.job_id for job in jobs} == {
        "JOB-001",
        "JOB-002",
    }


def test_job_store_lists_only_running_jobs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    store.save(
        _job(
            "JOB-RUNNING",
            GenerationJobStatus.RUNNING,
        )
    )
    store.save(
        _job(
            "JOB-CREATED",
            GenerationJobStatus.CREATED,
        )
    )

    jobs = store.list_running()

    assert [job.job_id for job in jobs] == ["JOB-RUNNING"]


def test_job_store_concurrent_writes_preserve_valid_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    def save_job(index: int) -> None:
        store.save(
            _job(
                "JOB-CONCURRENT",
                total_generated_rows=index,
            )
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(save_job, range(40)))

    loaded = store.get("MODEL-TEST", "JOB-CONCURRENT")

    assert loaded is not None
    assert loaded.job_id == "JOB-CONCURRENT"
    assert 0 <= loaded.total_generated_rows < 40


def test_failed_job_replacement_preserves_previous_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    original = _job("JOB-PRESERVE", total_generated_rows=10)
    store.save(original)

    def fail_replace(source: Path, destination: Path) -> None:
        raise PermissionError("access denied")

    monkeypatch.setattr(
        generation_file_persistence.os,
        "replace",
        fail_replace,
    )

    replacement = _job("JOB-PRESERVE", total_generated_rows=90)

    with pytest.raises(PersistenceOperationError, match="access denied"):
        store.save(replacement)

    loaded = store.get("MODEL-TEST", "JOB-PRESERVE")

    assert loaded is not None
    assert loaded.total_generated_rows == 10

    temporary_files = list(
        store._job_path("MODEL-TEST", "JOB-PRESERVE")
        .parent.glob(".job.json.*.tmp")
    )
    assert temporary_files == []



def test_job_store_returns_none_for_missing_record(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    assert store.get("MODEL-TEST", "JOB-MISSING") is None


def test_job_store_rejects_invalid_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    path = store._job_path("MODEL-TEST", "JOB-CORRUPT")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(JobRecordCorruptError, match="invalid JSON"):
        store.get("MODEL-TEST", "JOB-CORRUPT")


def test_job_store_rejects_invalid_record_schema(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    path = store._job_path("MODEL-TEST", "JOB-INVALID")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"data_model_id": "MODEL-TEST"}),
        encoding="utf-8",
    )

    with pytest.raises(JobRecordValidationError):
        store.get("MODEL-TEST", "JOB-INVALID")


def test_job_store_persists_attempt_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    job = _job("JOB-ATTEMPT", attempt_id="attempt-123")

    store.save(job)
    loaded = store.get("MODEL-TEST", "JOB-ATTEMPT")

    assert loaded is not None
    assert loaded.attempt_id == "attempt-123"


def test_job_store_rejects_public_response_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    public_job = GenerationJobResponse(
        data_model_id="MODEL-TEST",
        job_id="JOB-PUBLIC",
        status=GenerationJobStatus.CREATED,
        created_at=datetime.now(timezone.utc),
        total_target_rows=100,
    )

    with pytest.raises(TypeError, match="GenerationJobRecord"):
        store.save(public_job)


def test_attempt_id_is_not_exposed_by_public_response_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    store.save(_job("JOB-PRIVATE", attempt_id="private-attempt"))

    persisted = store.get("MODEL-TEST", "JOB-PRIVATE")
    assert persisted is not None

    public_response = GenerationJobResponse.model_validate(
        persisted.model_dump()
    )

    assert "attempt_id" not in public_response.model_dump()


def test_job_store_round_trips_preparation_phase_and_resume_intent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    job = _job(
        "JOB-LIFECYCLE",
        status=GenerationJobStatus.PREPARING,
        attempt_id="attempt-new",
    )
    job.preparation_phase = GenerationPreparationPhase.CHECKPOINT_PENDING
    job.resume_intent = GenerationResumeIntent(
        previous_attempt_id="attempt-old",
        new_attempt_id="attempt-new",
    )

    store.save(job)
    loaded = store.get("MODEL-TEST", "JOB-LIFECYCLE")

    assert loaded is not None
    assert (
        loaded.preparation_phase
        == GenerationPreparationPhase.CHECKPOINT_PENDING
    )
    assert loaded.resume_intent is not None
    assert loaded.resume_intent.previous_attempt_id == "attempt-old"
    assert loaded.resume_intent.new_attempt_id == "attempt-new"


def test_resume_intent_rejects_identical_attempt_ids() -> None:
    with pytest.raises(ValidationError):
        GenerationResumeIntent(
            previous_attempt_id="attempt-001",
            new_attempt_id="attempt-001",
        )


@pytest.mark.parametrize(
    ("previous_attempt_id", "new_attempt_id"),
    [
        ("", "attempt-new"),
        ("   ", "attempt-new"),
        ("attempt-old", ""),
        ("attempt-old", "   "),
    ],
)
def test_resume_intent_rejects_blank_attempt_ids(
    previous_attempt_id: str,
    new_attempt_id: str,
) -> None:
    with pytest.raises(ValidationError):
        GenerationResumeIntent(
            previous_attempt_id=previous_attempt_id,
            new_attempt_id=new_attempt_id,
        )


def test_resume_intent_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        GenerationResumeIntent(
            previous_attempt_id="attempt-old",
            new_attempt_id="attempt-new",
            unexpected="value",
        )


def test_job_store_loads_records_without_new_lifecycle_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    job = _job("JOB-LEGACY")

    payload = job.model_dump(
        mode="json",
        exclude={"throughput_rows_per_second"},
    )
    payload.pop("preparation_phase", None)
    payload.pop("resume_intent", None)

    path = store._job_path("MODEL-TEST", "JOB-LEGACY")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = store.get("MODEL-TEST", "JOB-LEGACY")

    assert loaded is not None
    assert loaded.preparation_phase is None
    assert loaded.resume_intent is None


def test_lifecycle_fields_are_not_exposed_by_public_response_model() -> None:
    job = _job(
        "JOB-PRIVATE-LIFECYCLE",
        status=GenerationJobStatus.PREPARING,
        attempt_id="attempt-new",
    )
    job.preparation_phase = GenerationPreparationPhase.CHECKPOINT_READY
    job.resume_intent = GenerationResumeIntent(
        previous_attempt_id="attempt-old",
        new_attempt_id="attempt-new",
    )

    public_response = GenerationJobResponse.model_validate(
        job.model_dump()
    )

    public_payload = public_response.model_dump()

    assert "attempt_id" not in public_payload
    assert "preparation_phase" not in public_payload
    assert "resume_intent" not in public_payload


def test_job_store_lists_jobs_with_recoverable_resume_intents(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    store.save(_job("JOB-PREPARING", GenerationJobStatus.PREPARING))
    store.save(_job("JOB-RUNNING", GenerationJobStatus.RUNNING))
    store.save(_job("JOB-INTERRUPTED", GenerationJobStatus.INTERRUPTED))

    interrupted_resume = _job(
        "JOB-INTERRUPTED-RESUME",
        GenerationJobStatus.INTERRUPTED,
        attempt_id="attempt-old",
    )
    interrupted_resume.resume_intent = GenerationResumeIntent(
        previous_attempt_id="attempt-old",
        new_attempt_id="attempt-new",
    )
    store.save(interrupted_resume)

    store.save(_job("JOB-CREATED", GenerationJobStatus.CREATED))

    jobs = store.list_recoverable()

    assert {job.job_id for job in jobs} == {
        "JOB-PREPARING",
        "JOB-RUNNING",
        "JOB-INTERRUPTED-RESUME",
    }




@pytest.mark.parametrize(
    "legacy_throughput",
    [2991.9666892163928, 2991, None],
)
def test_job_store_loads_legacy_throughput_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    legacy_throughput,
) -> None:
    """Legacy computed throughput is ignored and recalculated."""
    store = _store(tmp_path, monkeypatch)

    job = _job(
        "JOB-LEGACY-THROUGHPUT",
        total_generated_rows=50,
    )
    store.save(job)

    job_path = next(tmp_path.rglob("job.json"))
    payload = json.loads(job_path.read_text())

    payload.update({
        "started_at": "2026-01-01T10:00:00Z",
        "completed_at": "2026-01-01T10:00:02Z",
        "elapsed_seconds": 2.0,
        "throughput_rows_per_second": legacy_throughput,
    })

    job_path.write_text(json.dumps(payload, indent=2))

    loaded = store.get("MODEL-TEST", "JOB-LEGACY-THROUGHPUT")

    assert loaded is not None
    assert loaded.total_generated_rows == 50
    assert loaded.elapsed_seconds == 2.0
    assert loaded.throughput_rows_per_second == 25.0


@pytest.mark.parametrize(
    "invalid_throughput",
    [
        -1,
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
        "2991.96",
    ],
)
def test_job_store_rejects_invalid_legacy_throughput(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_throughput,
) -> None:
    store = _store(tmp_path, monkeypatch)

    store.save(_job("JOB-INVALID-LEGACY"))
    job_path = next(tmp_path.rglob("job.json"))
    payload = json.loads(job_path.read_text())

    payload["throughput_rows_per_second"] = invalid_throughput
    job_path.write_text(json.dumps(payload, indent=2))

    with pytest.raises(JobRecordValidationError):
        store.get("MODEL-TEST", "JOB-INVALID-LEGACY")


def test_job_store_still_rejects_unrelated_legacy_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    store.save(_job("JOB-UNKNOWN-LEGACY-FIELD"))
    job_path = next(tmp_path.rglob("job.json"))
    payload = json.loads(job_path.read_text())

    payload["unexpected_legacy_field"] = "must-not-be-accepted"
    job_path.write_text(json.dumps(payload, indent=2))

    with pytest.raises(JobRecordValidationError):
        store.get("MODEL-TEST", "JOB-UNKNOWN-LEGACY-FIELD")
