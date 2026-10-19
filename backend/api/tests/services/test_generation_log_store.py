from pathlib import Path

from app.models.generation_log_model import GenerationLogEntry
from app.services.generation_log_store import GenerationLogStore


def _store(root: Path) -> GenerationLogStore:
    return GenerationLogStore(root=root)


def _entry(status: str = "STARTED") -> GenerationLogEntry:
    return GenerationLogEntry(
        sequence=0,
        stage="ENTITY_GENERATION",
        status=status,
        entity_name="PART",
    )


def test_append_preserves_sequence_and_order(tmp_path: Path) -> None:
    store = _store(tmp_path)

    store.create(data_model_id="MODEL-1", job_id="JOB-1")
    first = store.append(
        data_model_id="MODEL-1",
        job_id="JOB-1",
        entry=_entry("STARTED"),
    )
    second = store.append(
        data_model_id="MODEL-1",
        job_id="JOB-1",
        entry=_entry("COMPLETED"),
    )

    document = store.get(data_model_id="MODEL-1", job_id="JOB-1")

    assert document is not None
    assert [entry.sequence for entry in document.entries] == [1, 2]
    assert [entry.status for entry in document.entries] == [
        "STARTED",
        "COMPLETED",
    ]
    assert first.sequence == 1
    assert second.sequence == 2
    assert all(entry.timestamp for entry in document.entries)


def test_append_reloads_existing_journal_in_new_store(tmp_path: Path) -> None:
    first_store = _store(tmp_path)
    first_store.create(data_model_id="MODEL-1", job_id="JOB-1")
    first_store.append(
        data_model_id="MODEL-1",
        job_id="JOB-1",
        entry=_entry(),
    )

    second_store = _store(tmp_path)
    recorded = second_store.append(
        data_model_id="MODEL-1",
        job_id="JOB-1",
        entry=_entry("COMPLETED"),
    )

    document = first_store.get(data_model_id="MODEL-1", job_id="JOB-1")

    assert recorded.sequence == 2
    assert document is not None
    assert [entry.sequence for entry in document.entries] == [1, 2]


def test_append_without_create_initializes_journal(tmp_path: Path) -> None:
    store = _store(tmp_path)

    recorded = store.append(
        data_model_id="MODEL-1",
        job_id="JOB-1",
        entry=_entry(),
    )

    document = store.get(data_model_id="MODEL-1", job_id="JOB-1")

    assert recorded.sequence == 1
    assert document is not None
    assert document.data_model_id == "MODEL-1"
    assert document.job_id == "JOB-1"
    assert len(document.entries) == 1


def test_event_journal_reloads_and_preserves_legacy_snapshot_entries(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create(data_model_id="MODEL-1", job_id="JOB-LEGACY")
    store.append(
        data_model_id="MODEL-1",
        job_id="JOB-LEGACY",
        entry=_entry("STARTED"),
    )

    event_path = (
        tmp_path
        / "MODEL-1"
        / "generation"
        / "JOB-LEGACY"
        / "generation_log.events.jsonl"
    )

    # Materialize the first entry into the legacy JSON snapshot.
    existing = store.get(
        data_model_id="MODEL-1",
        job_id="JOB-LEGACY",
    )
    assert existing is not None
    store.save(existing)
    event_path.unlink()

    # Continue from the legacy snapshot without the sidecar journal.
    store.append(
        data_model_id="MODEL-1",
        job_id="JOB-LEGACY",
        entry=_entry("COMPLETED"),
    )

    reloaded = _store(tmp_path).get(
        data_model_id="MODEL-1",
        job_id="JOB-LEGACY",
    )

    assert reloaded is not None
    assert [entry.sequence for entry in reloaded.entries] == [1, 2]


def test_event_journal_is_durable_and_snapshot_refreshes(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create(data_model_id="MODEL-1", job_id="JOB-SNAPSHOT")

    for _ in range(100):
        store.append(
            data_model_id="MODEL-1",
            job_id="JOB-SNAPSHOT",
            entry=_entry(),
        )

    root = (
        tmp_path
        / "MODEL-1"
        / "generation"
        / "JOB-SNAPSHOT"
    )
    snapshot = (root / "generation_log.json").read_text(encoding="utf-8")
    journal_lines = (
        root / "generation_log.events.jsonl"
    ).read_text(encoding="utf-8").splitlines()

    assert len(journal_lines) == 100
    assert len(__import__("json").loads(snapshot)["entries"]) == 100

    reloaded = _store(tmp_path).get(
        data_model_id="MODEL-1",
        job_id="JOB-SNAPSHOT",
    )
    assert reloaded is not None
    assert len(reloaded.entries) == 100
    assert [entry.sequence for entry in reloaded.entries] == list(range(1, 101))


def test_truncated_final_journal_record_preserves_prior_entries(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create(data_model_id="MODEL-1", job_id="JOB-RECOVERY")
    store.append(
        data_model_id="MODEL-1",
        job_id="JOB-RECOVERY",
        entry=_entry(),
    )

    event_path = (
        tmp_path
        / "MODEL-1"
        / "generation"
        / "JOB-RECOVERY"
        / "generation_log.events.jsonl"
    )
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write('{"sequence":2,"stage":"ENTITY_GENERATION"')

    reloaded = _store(tmp_path).get(
        data_model_id="MODEL-1",
        job_id="JOB-RECOVERY",
    )

    assert reloaded is not None
    assert [entry.sequence for entry in reloaded.entries] == [1]


def test_malformed_middle_journal_record_is_rejected(
    tmp_path: Path,
) -> None:
    import json

    import pytest

    store = _store(tmp_path)
    store.create(data_model_id="MODEL-1", job_id="JOB-CORRUPT")

    event_path = (
        tmp_path
        / "MODEL-1"
        / "generation"
        / "JOB-CORRUPT"
        / "generation_log.events.jsonl"
    )
    valid = _entry().model_dump(mode="json")
    valid["sequence"] = 1
    with event_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(valid) + "\n")
        handle.write('{"sequence":broken}' + "\n")
        valid["sequence"] = 3
        handle.write(json.dumps(valid) + "\n")

    with pytest.raises(ValueError, match="Invalid generation journal entry"):
        store.get(data_model_id="MODEL-1", job_id="JOB-CORRUPT")


def test_terminal_event_refreshes_snapshot_immediately(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create(data_model_id="MODEL-1", job_id="JOB-TERMINAL")
    store.append(
        data_model_id="MODEL-1",
        job_id="JOB-TERMINAL",
        entry=GenerationLogEntry(
            sequence=0,
            stage="COMPLETED",
            status="COMPLETED",
            entity_name="PART",
        ),
    )

    snapshot_path = (
        tmp_path
        / "MODEL-1"
        / "generation"
        / "JOB-TERMINAL"
        / "generation_log.json"
    )
    import json
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    assert len(snapshot["entries"]) == 1
    assert snapshot["entries"][0]["stage"] == "COMPLETED"
