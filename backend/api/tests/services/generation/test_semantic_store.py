from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.services.generation_semantic_store import (
    GenerationSemanticStore,
    SemanticStoreIntegrityError,
)


DATA_MODEL_ID = "FORGE-DATA-MODEL-TEST"
JOB_ID = "FORGE-TEST"


def _store(tmp_path: Path, monkeypatch) -> GenerationSemanticStore:
    store = GenerationSemanticStore()
    monkeypatch.setattr(store, "_root", tmp_path)
    return store


def _semantic_file(store: GenerationSemanticStore) -> Path:
    return store._semantic_path(DATA_MODEL_ID, JOB_ID)


def _commit(
    store: GenerationSemanticStore,
    values_by_row: dict[int, str],
) -> None:
    store.commit_unique_values(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row=values_by_row,
    )


def _get_unique(store: GenerationSemanticStore) -> dict[int, str]:
    return store.get_unique_values(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )


def test_unique_values_are_persisted_by_global_row_index(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    _commit(store, {
        0: "Hydraulic Pump",
        1: "Flight Control Computer",
        100: "Landing Gear Assembly",
    })

    assert _get_unique(store) == {
        0: "Hydraulic Pump",
        1: "Flight Control Computer",
        100: "Landing Gear Assembly",
    }


def test_sparse_unique_positions_remain_sparse(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    _commit(store, {
        0: "Product 001",
        1: "Product 002",
    })
    _commit(store, {
        100: "Product 101",
        101: "Product 102",
    })

    values = _get_unique(store)

    assert sorted(values) == [0, 1, 100, 101]
    assert 2 not in values
    assert 99 not in values
    assert values[100] == "Product 101"


def test_missing_unique_positions_can_be_filled_without_shifting_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    _commit(store, {
        0: "Product 001",
        1: "Product 002",
        100: "Product 101",
    })

    _commit(store, {
        2: "Product 003",
        3: "Product 004",
        4: "Product 005",
    })

    values = _get_unique(store)

    assert values[0] == "Product 001"
    assert values[1] == "Product 002"
    assert values[2] == "Product 003"
    assert values[4] == "Product 005"
    assert values[100] == "Product 101"


def test_identical_unique_row_write_is_idempotent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    batch = {
        0: "Hydraulic Pump",
        1: "Flight Control Computer",
    }

    _commit(store, batch)
    original_content = _semantic_file(store).read_text(encoding="utf-8")

    _commit(store, batch)

    assert _semantic_file(store).read_text(encoding="utf-8") == original_content
    assert _get_unique(store) == batch


def test_conflicting_value_for_existing_row_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    _commit(store, {0: "Hydraulic Pump"})

    with pytest.raises(
        SemanticStoreIntegrityError,
        match="Conflicting UNIQUE semantic value",
    ):
        _commit(store, {0: "Landing Gear Assembly"})

    assert _get_unique(store) == {0: "Hydraulic Pump"}


def test_duplicate_unique_values_across_different_rows_are_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    _commit(store, {0: "Hydraulic Pump"})

    with pytest.raises(
        SemanticStoreIntegrityError,
        match="Duplicate UNIQUE semantic values",
    ):
        _commit(store, {1: " hydraulic pump "})

    assert _get_unique(store) == {0: "Hydraulic Pump"}


def test_duplicate_values_inside_one_batch_are_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with pytest.raises(
        SemanticStoreIntegrityError,
        match="Duplicate UNIQUE semantic values",
    ):
        _commit(store, {
            0: "Hydraulic Pump",
            1: " hydraulic pump ",
        })

    assert _get_unique(store) == {}


@pytest.mark.parametrize(
    "row_index",
    [-1, True, 1.5, "1", None],
)
def test_invalid_global_row_indices_are_rejected(
    tmp_path: Path,
    monkeypatch,
    row_index,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with pytest.raises(SemanticStoreIntegrityError):
        _commit(store, {row_index: "Hydraulic Pump"})


@pytest.mark.parametrize("value", ["", "   ", None, 42])
def test_invalid_unique_values_are_rejected(
    tmp_path: Path,
    monkeypatch,
    value,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with pytest.raises(SemanticStoreIntegrityError):
        _commit(store, {0: value})


def test_empty_unique_mapping_does_not_create_semantic_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    _commit(store, {})

    assert _get_unique(store) == {}
    assert not _semantic_file(store).exists()


def test_vocabulary_values_are_persisted_and_retrieved(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    vocabulary = [
        "Hydraulics",
        "Avionics",
        "Landing Systems",
    ]

    store.save_vocabulary(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        entity_name="PRODUCT",
        field_name="PRODUCT_GROUP",
        values=vocabulary,
    )

    result = store.get(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        entity_name="PRODUCT",
        field_name="PRODUCT_GROUP",
    )

    assert result is not None
    assert result["mode"] == "VOCABULARY"
    assert result["values"] == vocabulary


def test_identical_vocabulary_write_is_idempotent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    vocabulary = ["Hydraulics", "Avionics"]

    kwargs = {
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "entity_name": "PRODUCT",
        "field_name": "PRODUCT_GROUP",
        "values": vocabulary,
    }

    store.save_vocabulary(**kwargs)
    original_content = _semantic_file(store).read_text(encoding="utf-8")

    store.save_vocabulary(**kwargs)

    assert _semantic_file(store).read_text(encoding="utf-8") == original_content


def test_conflicting_vocabulary_replacement_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    store.save_vocabulary(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        entity_name="PRODUCT",
        field_name="PRODUCT_GROUP",
        values=["Hydraulics", "Avionics"],
    )

    with pytest.raises(
        SemanticStoreIntegrityError,
        match="replacement is not allowed",
    ):
        store.save_vocabulary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name="PRODUCT",
            field_name="PRODUCT_GROUP",
            values=["Hydraulics", "Landing Systems"],
        )


def test_unique_and_vocabulary_modes_cannot_be_mixed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    _commit(store, {0: "Hydraulic Pump"})

    with pytest.raises(SemanticStoreIntegrityError):
        store.save_vocabulary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
            values=["Hydraulic Pump"],
        )

    store.save_vocabulary(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        entity_name="PRODUCT",
        field_name="PRODUCT_GROUP",
        values=["Hydraulics", "Avionics"],
    )

    with pytest.raises(SemanticStoreIntegrityError):
        store.get_unique_values(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name="PRODUCT",
            field_name="PRODUCT_GROUP",
        )

    with pytest.raises(SemanticStoreIntegrityError):
        store.commit_unique_values(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name="PRODUCT",
            field_name="PRODUCT_GROUP",
            values_by_row={0: "Hydraulics"},
        )


def test_multiple_fields_preserve_existing_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    _commit(store, {0: "Hydraulic Pump"})

    store.save_vocabulary(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        entity_name="PRODUCT",
        field_name="PRODUCT_GROUP",
        values=["Hydraulics", "Avionics"],
    )

    document = store.get_all(DATA_MODEL_ID, JOB_ID)

    assert set(document["fields"]) == {
        "PRODUCT.PRODUCT_NAME",
        "PRODUCT.PRODUCT_GROUP",
    }


def test_store_survives_new_instance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    first_store = _store(tmp_path, monkeypatch)
    _commit_values = {
        0: "Hydraulic Pump",
        100: "Landing Gear Assembly",
    }
    first_store.commit_unique_values(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row=_commit_values,
    )

    second_store = _store(tmp_path, monkeypatch)

    assert _get_unique(second_store) == _commit_values


def test_missing_store_returns_empty_document(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    document = store.get_all(DATA_MODEL_ID, JOB_ID)

    assert document == {
        "schema_version": "2.0",
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "fields": {},
    }


def test_corrupt_json_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)
    path.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(
        SemanticStoreIntegrityError,
        match="cannot be parsed",
    ):
        store.get_all(DATA_MODEL_ID, JOB_ID)


def test_v1_document_is_rejected_without_migration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "job_id": JOB_ID,
            "fields": {},
        }),
        encoding="utf-8",
    )

    with pytest.raises(
        SemanticStoreIntegrityError,
        match="schema version",
    ):
        store.get_all(DATA_MODEL_ID, JOB_ID)


def test_wrong_data_model_id_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)

    path.write_text(
        json.dumps({
            "schema_version": "2.0",
            "data_model_id": "ANOTHER-MODEL",
            "job_id": JOB_ID,
            "fields": {},
        }),
        encoding="utf-8",
    )

    with pytest.raises(
        SemanticStoreIntegrityError,
        match="data model ID",
    ):
        store.get_all(DATA_MODEL_ID, JOB_ID)


def test_wrong_job_id_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)

    path.write_text(
        json.dumps({
            "schema_version": "2.0",
            "data_model_id": DATA_MODEL_ID,
            "job_id": "ANOTHER-JOB",
            "fields": {},
        }),
        encoding="utf-8",
    )

    with pytest.raises(
        SemanticStoreIntegrityError,
        match="job ID",
    ):
        store.get_all(DATA_MODEL_ID, JOB_ID)



@pytest.mark.parametrize(
    "row_key",
    [
        "01",
        "9" * 5000,
        "9223372036854775808",
    ],
)
def test_malformed_unique_row_mapping_is_rejected(
    tmp_path: Path,
    monkeypatch,
    row_key: str,
) -> None:
    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)

    path.write_text(
        json.dumps({
            "schema_version": "2.0",
            "data_model_id": DATA_MODEL_ID,
            "job_id": JOB_ID,
            "fields": {
                "PRODUCT.PRODUCT_NAME": {
                    "entity_name": "PRODUCT",
                    "field_name": "PRODUCT_NAME",
                    "mode": "UNIQUE",
                    "values_by_row": {
                        row_key: "Hydraulic Pump",
                    },
                },
            },
        }),
        encoding="utf-8",
    )

    with pytest.raises(
        SemanticStoreIntegrityError,
        match="Invalid row index",
    ):
        store.get_all(DATA_MODEL_ID, JOB_ID)


def test_save_does_not_overwrite_corrupt_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)

    original = "{corrupt persisted state"
    path.write_text(original, encoding="utf-8")

    with pytest.raises(SemanticStoreIntegrityError):
        store.save_vocabulary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name="PRODUCT",
            field_name="PRODUCT_GROUP",
            values=["Hydraulics"],
        )

    assert path.read_text(encoding="utf-8") == original


def test_concurrent_unique_writes_preserve_all_row_assignments(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    def commit_batch(batch_number: int) -> None:
        start = batch_number * 10
        values = {
            row_index: f"PRODUCT-{row_index:04d}"
            for row_index in range(start, start + 10)
        }
        _commit(store, values)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(commit_batch, range(20)))

    values = _get_unique(store)

    assert len(values) == 200
    assert set(values) == set(range(200))
    assert len({value.casefold() for value in values.values()}) == 200


def test_concurrent_saves_preserve_different_semantic_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    def save_vocabulary(index: int) -> None:
        store.save_vocabulary(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name="PRODUCT",
            field_name=f"FIELD_{index}",
            values=[f"VALUE_{index}"],
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(save_vocabulary, range(20)))

    fields = store.get_all(DATA_MODEL_ID, JOB_ID)["fields"]

    assert len(fields) == 20

    for index in range(20):
        assert fields[f"PRODUCT.FIELD_{index}"]["values"] == [
            f"VALUE_{index}"
        ]


@pytest.mark.parametrize(
    "component",
    [
        "",
        ".",
        "..",
        "../OTHER",
        r"..\OTHER",
        "MODEL/OTHER",
        "MODEL\\OTHER",
        "CON",
        "con.txt",
        "NUL",
        "COM1",
        "LPT9",
        "trailing.",
        "trailing ",
    ],
)
def test_invalid_path_components_are_rejected(
    tmp_path: Path,
    monkeypatch,
    component: str,
) -> None:
    store = _store(tmp_path, monkeypatch)

    with pytest.raises(ValueError):
        store._semantic_path(component, JOB_ID)

def test_semantic_path_rejects_model_directory_symlink_escape(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()

    model_link = tmp_path / DATA_MODEL_ID
    try:
        model_link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Directory symlinks unavailable: {exc}")

    with pytest.raises(ValueError, match="escapes"):
        store._semantic_path(DATA_MODEL_ID, JOB_ID)


def test_semantic_path_rejects_semantic_file_symlink_escape(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)

    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    outside.write_text("external state", encoding="utf-8")

    try:
        path.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"File symlinks unavailable: {exc}")

    with pytest.raises(ValueError, match="escapes"):
        store._semantic_path(DATA_MODEL_ID, JOB_ID)
