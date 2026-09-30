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
