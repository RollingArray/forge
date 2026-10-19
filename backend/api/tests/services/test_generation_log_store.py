import json
from pathlib import Path

import pytest

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


def _event_path(root: Path, job_id: str) -> Path:
    return (
        root
        / "MODEL-1"
        / "generation"
        / job_id
        / "generation_log.events.jsonl"
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


def test_create_initializes_only_jsonl_journal(tmp_path: Path) -> None:
    store = _store(tmp_path)
    document = store.create(
        data_model_id="MODEL-1",
        job_id="JOB-ONLY-JSONL",
    )

    directory = tmp_path / "MODEL-1" / "generation" / "JOB-ONLY-JSONL"

    assert document.entries == []
    assert (directory / "generation_log.events.jsonl").is_file()
    assert (directory / "generation_log.events.jsonl").read_text(
        encoding="utf-8"
    ) == ""
    assert not (directory / "generation_log.json").exists()


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

    document = _store(tmp_path).get(
        data_model_id="MODEL-1",
        job_id="JOB-1",
    )

    assert recorded.sequence == 1
    assert document is not None
    assert document.data_model_id == "MODEL-1"
    assert document.job_id == "JOB-1"
    assert len(document.entries) == 1


def test_jsonl_is_durable_and_history_survives_store_restart(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create(data_model_id="MODEL-1", job_id="JOB-DURABLE")

    for _ in range(100):
        store.append(
            data_model_id="MODEL-1",
            job_id="JOB-DURABLE",
            entry=_entry(),
        )

    event_path = _event_path(tmp_path, "JOB-DURABLE")
    journal_lines = event_path.read_text(encoding="utf-8").splitlines()

    assert len(journal_lines) == 100
    assert not event_path.with_name("generation_log.json").exists()

    reloaded = _store(tmp_path).get(
        data_model_id="MODEL-1",
        job_id="JOB-DURABLE",
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

    event_path = _event_path(tmp_path, "JOB-RECOVERY")
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
    store = _store(tmp_path)
    event_path = _event_path(tmp_path, "JOB-CORRUPT")
    event_path.parent.mkdir(parents=True, exist_ok=True)

    valid = _entry().model_dump(mode="json")
    valid["sequence"] = 1
    with event_path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(valid) + "\n")
        handle.write('{"sequence":broken}\n')
        valid["sequence"] = 3
        handle.write(json.dumps(valid) + "\n")

    with pytest.raises(ValueError, match="Invalid generation journal entry"):
        store.get(data_model_id="MODEL-1", job_id="JOB-CORRUPT")


def test_terminal_event_is_durable_without_snapshot(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create(data_model_id="MODEL-1", job_id="JOB-TERMINAL")
    store.append(
        data_model_id="MODEL-1",
        job_id="JOB-TERMINAL",
        entry=GenerationLogEntry(
            sequence=0,
            stage="FAILED",
            status="FAILED",
            entity_name="PART",
        ),
    )

    event_path = _event_path(tmp_path, "JOB-TERMINAL")
    records = [
        json.loads(line)
        for line in event_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 1
    assert records[0]["stage"] == "FAILED"
    assert not event_path.with_name("generation_log.json").exists()

    reloaded = _store(tmp_path).get(
        data_model_id="MODEL-1",
        job_id="JOB-TERMINAL",
    )
    assert reloaded is not None
    assert len(reloaded.entries) == 1
    assert reloaded.entries[0].stage == "FAILED"


def test_transient_activity_is_not_persisted_and_sequences_stay_unique(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create(data_model_id="MODEL-1", job_id="JOB-LIVE")

    live = store.append(
        data_model_id="MODEL-1",
        job_id="JOB-LIVE",
        entry=GenerationLogEntry(
            sequence=0,
            stage="FIELD_GENERATION",
            status="STARTED",
            entity_name="PART",
            field_name="PART_ID",
            chunk_number=1,
        ),
        persist=False,
    )

    event_path = _event_path(tmp_path, "JOB-LIVE")
    assert live.sequence == 1
    assert live.timestamp
    assert event_path.read_text(encoding="utf-8") == ""

    durable = store.append(
        data_model_id="MODEL-1",
        job_id="JOB-LIVE",
        entry=_entry("COMPLETED"),
    )
    assert durable.sequence == 2

    reloaded = _store(tmp_path).get(
        data_model_id="MODEL-1",
        job_id="JOB-LIVE",
    )
    assert reloaded is not None
    assert [entry.sequence for entry in reloaded.entries] == [2]
