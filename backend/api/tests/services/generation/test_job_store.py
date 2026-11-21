from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.models.generation_model import (
    GenerationJobResponse,
    GenerationJobStatus,
)
from app.services import generation_file_persistence
from app.services.generation_job_store import GenerationJobStore


def _job(
    job_id: str,
    status: GenerationJobStatus = GenerationJobStatus.CREATED,
    total_generated_rows: int = 0,
) -> GenerationJobResponse:
    return GenerationJobResponse(
        data_model_id="MODEL-TEST",
        job_id=job_id,
        status=status,
        created_at=datetime.now(timezone.utc),
        total_target_rows=100,
        total_generated_rows=total_generated_rows,
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

    with pytest.raises(PermissionError, match="access denied"):
        store.save(replacement)

    loaded = store.get("MODEL-TEST", "JOB-PRESERVE")

    assert loaded is not None
    assert loaded.total_generated_rows == 10

    temporary_files = list(
        store._job_path("MODEL-TEST", "JOB-PRESERVE")
        .parent.glob(".job.json.*.tmp")
    )
    assert temporary_files == []
