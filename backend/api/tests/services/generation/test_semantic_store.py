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
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        mode="UNIQUE",
        values=values,
    )

    result = store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
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
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        mode="UNIQUE",
        values=product_names,
    )

    store.save(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_GROUP",
        mode="VOCABULARY",
        values=product_groups,
    )

    first = store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    second = store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
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
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        mode="UNIQUE",
        values=values,
    )

    second_store = _store(tmp_path, monkeypatch)

    result = second_store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    assert result is not None
    assert result["values"] == values
    assert result["mode"] == "UNIQUE"


def test_append_unique_rejects_duplicates_in_first_batch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    try:
        store.append_unique(
            data_model_id="FORGE-DATA-MODEL-TEST",
            job_id="FORGE-TEST",
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
            values=["Hydraulic Pump", " hydraulic pump "],
        )
    except ValueError as exc:
        assert "Duplicate UNIQUE semantic values" in str(exc)
    else:
        raise AssertionError("Expected duplicate first batch to be rejected.")

    assert store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    ) is None


def test_append_unique_rejects_duplicates_across_batches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    store.append_unique(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values=["Hydraulic Pump", "Flight Control Computer"],
    )

    try:
        store.append_unique(
            data_model_id="FORGE-DATA-MODEL-TEST",
            job_id="FORGE-TEST",
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
            values=["Landing Gear Assembly", " hydraulic pump "],
        )
    except ValueError as exc:
        assert "Duplicate UNIQUE semantic values" in str(exc)
    else:
        raise AssertionError("Expected cross-batch duplicate to be rejected.")

    result = store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    assert result is not None
    assert result["values"] == [
        "Hydraulic Pump",
        "Flight Control Computer",
    ]


def test_append_unique_rejects_blank_values_in_first_batch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = _store(tmp_path, monkeypatch)

    try:
        store.append_unique(
            data_model_id="FORGE-DATA-MODEL-TEST",
            job_id="FORGE-TEST",
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
            values=["Hydraulic Pump", "   "],
        )
    except ValueError as exc:
        assert "non-empty strings" in str(exc)
    else:
        raise AssertionError("Expected blank semantic value to be rejected.")

    assert store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    ) is None


def _semantic_file(
    store: GenerationSemanticStore,
    data_model_id: str = "FORGE-DATA-MODEL-TEST",
    job_id: str = "FORGE-TEST",
) -> Path:
    return (
        store._semantic_path(data_model_id, job_id)
    )


def test_semantic_store_rejects_corrupt_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.services.generation_semantic_store import (
        SemanticStoreIntegrityError,
    )

    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)
    path.write_text("{invalid json", encoding="utf-8")

    try:
        store.get_all("FORGE-DATA-MODEL-TEST", "FORGE-TEST")
    except SemanticStoreIntegrityError as exc:
        assert "cannot be read or parsed" in str(exc)
    else:
        raise AssertionError("Corrupt semantic JSON must be rejected.")


def test_semantic_store_rejects_wrong_job_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import json

    from app.services.generation_semantic_store import (
        SemanticStoreIntegrityError,
    )

    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "job_id": "ANOTHER-JOB",
            "fields": {},
        }),
        encoding="utf-8",
    )

    try:
        store.get_all("FORGE-DATA-MODEL-TEST", "FORGE-TEST")
    except SemanticStoreIntegrityError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("A mismatched job ID must be rejected.")


def test_semantic_store_rejects_unsupported_schema_version(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import json

    from app.services.generation_semantic_store import (
        SemanticStoreIntegrityError,
    )

    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "schema_version": "2.0",
            "job_id": "FORGE-TEST",
            "fields": {},
        }),
        encoding="utf-8",
    )

    try:
        store.get_all("FORGE-DATA-MODEL-TEST", "FORGE-TEST")
    except SemanticStoreIntegrityError as exc:
        assert "schema version" in str(exc)
    else:
        raise AssertionError("An unsupported schema version must be rejected.")


def test_semantic_store_rejects_malformed_field_record(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import json

    from app.services.generation_semantic_store import (
        SemanticStoreIntegrityError,
    )

    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "job_id": "FORGE-TEST",
            "fields": {
                "PRODUCT.PRODUCT_NAME": {
                    "entity_name": "PRODUCT",
                    "field_name": "PRODUCT_NAME",
                    "mode": "UNIQUE",
                    "values": "not-a-list",
                },
            },
        }),
        encoding="utf-8",
    )

    try:
        store.get_all("FORGE-DATA-MODEL-TEST", "FORGE-TEST")
    except SemanticStoreIntegrityError as exc:
        assert "values are invalid" in str(exc)
    else:
        raise AssertionError("Malformed field values must be rejected.")


def test_save_does_not_overwrite_corrupt_semantic_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.services.generation_semantic_store import (
        SemanticStoreIntegrityError,
    )

    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)
    original = "{corrupt persisted state"
    path.write_text(original, encoding="utf-8")

    try:
        store.save(
            data_model_id="FORGE-DATA-MODEL-TEST",
            job_id="FORGE-TEST",
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
            mode="VOCABULARY",
            values=["Hydraulic Pump"],
        )
    except SemanticStoreIntegrityError:
        pass
    else:
        raise AssertionError("Save must reject corrupt existing state.")

    assert path.read_text(encoding="utf-8") == original


def test_semantic_store_rejects_duplicate_values_in_persisted_unique_field(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import json

    from app.services.generation_semantic_store import (
        SemanticStoreIntegrityError,
    )

    store = _store(tmp_path, monkeypatch)
    path = _semantic_file(store)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "job_id": "FORGE-TEST",
            "fields": {
                "PRODUCT.PRODUCT_NAME": {
                    "entity_name": "PRODUCT",
                    "field_name": "PRODUCT_NAME",
                    "mode": "UNIQUE",
                    "values": ["Hydraulic Pump", " hydraulic pump "],
                },
            },
        }),
        encoding="utf-8",
    )

    # Historical state remains inspectable, but cannot be used for
    # UNIQUE generation or extended with more values.
    document = store.get_all(
        "FORGE-DATA-MODEL-TEST",
        "FORGE-TEST",
    )
    assert "PRODUCT.PRODUCT_NAME" in document["fields"]

    try:
        store.get(
            data_model_id="FORGE-DATA-MODEL-TEST",
            job_id="FORGE-TEST",
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
        )
    except SemanticStoreIntegrityError as exc:
        assert "cannot safely resume" in str(exc)
    else:
        raise AssertionError(
            "A UNIQUE field with historical duplicates must not be resumed."
        )

    try:
        store.append_unique(
            data_model_id="FORGE-DATA-MODEL-TEST",
            job_id="FORGE-TEST",
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
            values=["New Product"],
        )
    except SemanticStoreIntegrityError:
        pass
    else:
        raise AssertionError(
            "A UNIQUE field with historical duplicates must not be extended."
        )
