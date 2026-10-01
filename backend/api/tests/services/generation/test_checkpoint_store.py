from pathlib import Path

from app.services.generation_checkpoint_store import (
    GenerationCheckpointStore,
)


def test_checkpoint_persists_committed_chunk_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = GenerationCheckpointStore()

    monkeypatch.setattr(
        store,
        "_root",
        tmp_path,
    )

    store.save(
        job_id="FORGE-TEST",
        seed=42,
        entities={
            "CUSTOMER": {
                "target_rows": 150,
                "chunk_size": 50,
                "total_chunks": 3,
                "committed_chunks": [1, 3],
                "committed_rows": 100,
            },
        },
    )

    checkpoint = store.get("FORGE-TEST")

    assert checkpoint is not None
    assert checkpoint["entities"]["CUSTOMER"][
        "committed_chunks"
    ] == [1, 3]
    assert checkpoint["entities"]["CUSTOMER"][
        "committed_rows"
    ] == 100


def test_checkpoint_preserves_non_contiguous_committed_chunks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = GenerationCheckpointStore()

    monkeypatch.setattr(
        store,
        "_root",
        tmp_path,
    )

    store.save(
        job_id="FORGE-TEST",
        seed=42,
        entities={
            "CUSTOMER": {
                "target_rows": 250,
                "chunk_size": 50,
                "total_chunks": 5,
                "committed_chunks": [1, 2, 5],
                "committed_rows": 150,
            },
        },
    )

    checkpoint = store.get("FORGE-TEST")

    assert checkpoint is not None
    assert checkpoint["entities"]["CUSTOMER"][
        "committed_chunks"
    ] == [1, 2, 5]


def test_is_chunk_committed_uses_durable_chunk_identity(
    tmp_path,
    monkeypatch,
) -> None:
    store = GenerationCheckpointStore()

    monkeypatch.setattr(
        store,
        "_root",
        tmp_path,
    )

    store.save(
        job_id="FORGE-TEST",
        seed=42,
        chunk_size=50,
        entities={
            "PRODUCT": {
                "target_rows": 250,
                "completed_chunks": [1, 2, 4],
            },
        },
    )

    assert store.is_chunk_committed(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        chunk_number=1,
    )

    assert not store.is_chunk_committed(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        chunk_number=3,
    )

    assert store.is_chunk_committed(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        chunk_number=4,
    )


def test_is_chunk_committed_returns_false_when_checkpoint_is_missing(
    tmp_path,
    monkeypatch,
) -> None:
    store = GenerationCheckpointStore()

    monkeypatch.setattr(
        store,
        "_root",
        tmp_path,
    )

    assert not store.is_chunk_committed(
        job_id="FORGE-MISSING",
        entity_name="PRODUCT",
        chunk_number=1,
    )


def test_get_committed_rows_returns_durable_entity_progress(
    tmp_path,
    monkeypatch,
) -> None:
    store = GenerationCheckpointStore()

    monkeypatch.setattr(
        store,
        "_root",
        tmp_path,
    )

    store.save(
        job_id="FORGE-TEST",
        seed=42,
        chunk_size=50,
        entities={
            "PRODUCT": {
                "target_rows": 1000,
                "completed_chunks": [1, 2, 3, 4, 5, 6],
            },
        },
    )

    assert store.get_committed_rows(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
    ) == 300

    assert store.get_committed_rows(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 0
