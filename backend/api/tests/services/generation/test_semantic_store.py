from pathlib import Path

from app.services.generation_semantic_store import (
    GenerationSemanticStore,
)


def _store(tmp_path: Path, monkeypatch) -> GenerationSemanticStore:
    store = GenerationSemanticStore()

    monkeypatch.setattr(
        store,
        "_root",
        tmp_path,
    )

    return store


def test_semantic_values_are_persisted_and_retrieved(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    values = [
        "Hydraulic Pump",
        "Flight Control Computer",
        "Landing Gear Assembly",
    ]

    store.save(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        mode="UNIQUE",
        values=values,
    )

    result = store.get(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    assert result is not None
    assert result["entity_name"] == "PRODUCT"
    assert result["field_name"] == "PRODUCT_NAME"
    assert result["mode"] == "UNIQUE"
    assert result["values"] == values


def test_saving_multiple_fields_preserves_existing_semantic_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    product_names = [
        "Hydraulic Pump",
        "Flight Control Computer",
    ]

    product_groups = [
        "Hydraulics",
        "Avionics",
        "Landing Systems",
    ]

    store.save(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        mode="UNIQUE",
        values=product_names,
    )

    store.save(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_GROUP",
        mode="VOCABULARY",
        values=product_groups,
    )

    first = store.get(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    second = store.get(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_GROUP",
    )

    assert first is not None
    assert first["mode"] == "UNIQUE"
    assert first["values"] == product_names

    assert second is not None
    assert second["mode"] == "VOCABULARY"
    assert second["values"] == product_groups


def test_semantic_store_survives_new_store_instance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    first_store = _store(tmp_path, monkeypatch)

    values = [
        "Hydraulic Pump",
        "Flight Control Computer",
    ]

    first_store.save(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        mode="UNIQUE",
        values=values,
    )

    second_store = _store(tmp_path, monkeypatch)

    result = second_store.get(
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    assert result is not None
    assert result["values"] == values
    assert result["mode"] == "UNIQUE"
