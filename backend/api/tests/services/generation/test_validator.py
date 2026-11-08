from __future__ import annotations

import csv
from pathlib import Path

from app.services.generation.artifact_reader import (
    GenerationArtifactReader,
)
from app.services.generation_checkpoint_store import (
    GenerationCheckpointStore,
)
from app.services.generation.validator import (
    GenerationValidator,
)


def _write_chunk(
    *,
    root: Path,
    job_id: str,
    entity_name: str,
    chunk_number: int,
    rows: list[dict[str, str]],
) -> None:
    directory = (
        root
        / "data_model"
        / "TEST-MODEL"
        / "generation"
        / job_id
        / "generated"
        / entity_name
        / "chunks"
    )
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = directory / f"chunk_{chunk_number:06d}.csv"

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def _validator(tmp_path: Path) -> GenerationValidator:
    reader = GenerationArtifactReader()
    reader._data_directory = tmp_path

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path / "data_model"

    reader._checkpoint_store = checkpoint_store

    return GenerationValidator(
        artifact_reader=reader,
    )


def _commit_chunks(
    *,
    root: Path,
    job_id: str,
    specification: dict,
) -> None:
    entities = {}
    generated_root = (
        root / "data_model" / "TEST-MODEL"
        / "generation" / job_id / "generated"
    )

    for entity in specification.get("entities", []):
        entity_name = entity["name"]
        chunk_directory = (
            generated_root / entity_name / "chunks"
        )
        chunk_numbers = sorted(
            int(path.stem.removeprefix("chunk_"))
            for path in chunk_directory.glob("chunk_*.csv")
            if path.stem.removeprefix("chunk_").isdigit()
        )

        entities[entity_name] = {
            "target_rows": entity.get("population", {}).get("count", 0),
            "completed_chunks": chunk_numbers,
        }

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = root / "data_model"

    checkpoint_store.save(
        data_model_id="TEST-MODEL",
        job_id=job_id,
        seed=1,
        entities=entities,
        chunk_size=100,
    )




def _semantic_unique_specification(
    *,
    field_name: str = "DESCRIPTION",
) -> dict:
    return {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 3},
                "fields": [
                    {"name": "ID", "type": "INTEGER"},
                    {
                        "name": field_name,
                        "type": "STRING",
                        "generation": {
                            "strategy": "RANDOM",
                            "generator": "SEMANTIC",
                            "parameters": {
                                "description": "Unique product description",
                                "mode": "UNIQUE",
                            },
                        },
                    },
                ],
                "identity": {"fields": ["ID"]},
            },
        ],
    }


def _semantic_rule(result, field_name: str = "DESCRIPTION") -> dict:
    rule_id = f"semantic_unique:PRODUCT.{field_name}"
    return next(
        rule
        for rule in result.evidence.rule_results
        if rule["rule_id"] == rule_id
    )


def test_semantic_unique_validation_detects_duplicates_across_chunks(
    tmp_path: Path,
) -> None:
    job_id = "SEM-UNIQUE-CROSS-CHUNK"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "DESCRIPTION": "Alpha"},
            {"ID": "2", "DESCRIPTION": "Beta"},
        ],
    )
    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=2,
        rows=[
            {"ID": "3", "DESCRIPTION": "Alpha"},
        ],
    )

    specification = _semantic_unique_specification()
    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    rule = _semantic_rule(result)
    assert not result.valid
    assert rule["status"] == "FAILED"
    assert rule["details"]["rows_checked"] == 3
    assert rule["details"]["duplicate_count"] == 1
    assert any("semantic UNIQUE field" in error for error in result.errors)


def test_semantic_unique_validation_normalizes_case_and_whitespace(
    tmp_path: Path,
) -> None:
    job_id = "SEM-UNIQUE-NORMALIZATION"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "DESCRIPTION": "Alpha"},
            {"ID": "2", "DESCRIPTION": "  aLPHa  "},
            {"ID": "3", "DESCRIPTION": "Beta"},
        ],
    )

    specification = _semantic_unique_specification()
    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    rule = _semantic_rule(result)
    assert not result.valid
    assert rule["status"] == "FAILED"
    assert rule["details"]["duplicate_count"] == 1


def test_semantic_unique_duplicate_fails_even_when_values_are_missing(
    tmp_path: Path,
) -> None:
    job_id = "SEM-UNIQUE-DUPLICATE-AND-MISSING"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "DESCRIPTION": "Alpha"},
            {"ID": "2", "DESCRIPTION": ""},
            {"ID": "3", "DESCRIPTION": " alpha "},
        ],
    )

    specification = _semantic_unique_specification()
    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    rule = _semantic_rule(result)
    assert rule["status"] == "FAILED"
    assert rule["details"]["duplicate_count"] == 1
    assert rule["details"]["missing_value_count"] == 1
    assert not result.valid


def test_semantic_unique_validation_passes_for_unique_values(
    tmp_path: Path,
) -> None:
    job_id = "SEM-UNIQUE-PASS"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "DESCRIPTION": "Alpha"},
            {"ID": "2", "DESCRIPTION": "Beta"},
            {"ID": "3", "DESCRIPTION": "Gamma"},
        ],
    )

    specification = _semantic_unique_specification()
    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    rule = _semantic_rule(result)
    assert rule["status"] == "PASSED"
    assert rule["details"]["rows_checked"] == 3
    assert rule["details"]["unique_values"] == 3


def test_semantic_unique_validation_does_not_pass_missing_values(
    tmp_path: Path,
) -> None:
    job_id = "SEM-UNIQUE-MISSING"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "DESCRIPTION": "Alpha"},
            {"ID": "2", "DESCRIPTION": ""},
            {"ID": "3", "DESCRIPTION": "Gamma"},
        ],
    )

    specification = _semantic_unique_specification()
    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    rule = _semantic_rule(result)
    assert rule["status"] == "NOT_EVALUATED"
    assert rule["details"]["missing_value_count"] == 1


def test_semantic_unique_validation_does_not_pass_unreadable_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    job_id = "SEM-UNIQUE-UNREADABLE"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "DESCRIPTION": "Alpha"},
            {"ID": "2", "DESCRIPTION": "Beta"},
            {"ID": "3", "DESCRIPTION": "Gamma"},
        ],
    )

    specification = _semantic_unique_specification()
    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    validator = _validator(tmp_path)
    original_iter = validator._iter_typed_rows

    def fail_on_semantic_scan(**kwargs):
        import inspect

        caller = inspect.currentframe().f_back
        if (
            caller is not None
            and caller.f_code.co_name == "validate"
            and caller.f_lineno >= 900
            and kwargs.get("entity_name") == "PRODUCT"
        ):
            raise OSError("simulated committed artifact read failure")

        yield from original_iter(**kwargs)

    monkeypatch.setattr(validator, "_iter_typed_rows", fail_on_semantic_scan)

    result = validator.validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    rule = _semantic_rule(result)
    assert rule["status"] == "NOT_EVALUATED"
    assert "simulated committed artifact read failure" in (
        rule["details"]["evaluation_error"]
    )


def test_validation_counts_committed_rows(
    tmp_path: Path,
) -> None:
    job_id = "JOB-1"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[
            {"ID": "1"},
            {"ID": "2"},
        ],
    )

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="CUSTOMER",
        chunk_number=2,
        rows=[
            {"ID": "3"},
        ],
    )

    specification = {
        "entities": [
            {
                "name": "CUSTOMER",
                "population": {"count": 3},
                "fields": [
                    {
                        "name": "ID",
                        "type": "INTEGER",
                    },
                ],
                "identity": {
                    "fields": ["ID"],
                },
            },
        ],
    }

    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    assert result.valid
    assert result.expected_rows == 3
    assert result.generated_rows == 3
    assert result.errors == []


def test_validation_detects_duplicate_identity(
    tmp_path: Path,
) -> None:
    job_id = "JOB-2"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[
            {"ID": "1"},
            {"ID": "1"},
        ],
    )

    specification = {
        "entities": [
            {
                "name": "CUSTOMER",
                "population": {"count": 2},
                "fields": [
                    {
                        "name": "ID",
                        "type": "INTEGER",
                    },
                ],
                "identity": {
                    "fields": ["ID"],
                },
            },
        ],
    }

    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    assert not result.valid
    assert any(
        "duplicate identity" in error
        for error in result.errors
    )


def test_validation_converts_numeric_csv_values_for_constraints(
    tmp_path: Path,
) -> None:
    job_id = "JOB-3"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "PRICE": "25.50"},
            {"ID": "2", "PRICE": "30.00"},
        ],
    )

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 2},
                "fields": [
                    {
                        "name": "ID",
                        "type": "INTEGER",
                    },
                    {
                        "name": "PRICE",
                        "type": "DECIMAL",
                    },
                ],
                "identity": {
                    "fields": ["ID"],
                },
            },
        ],
        "constraints": [
            {
                "entity": "PRODUCT",
                "field": "PRICE",
                "operator": ">",
                "value": 0,
            },
        ],
    }

    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    assert result.valid
    assert result.errors == []


def test_validation_detects_constraint_violation(
    tmp_path: Path,
) -> None:
    job_id = "JOB-4"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "PRICE": "-5.00"},
        ],
    )

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 1},
                "fields": [
                    {
                        "name": "ID",
                        "type": "INTEGER",
                    },
                    {
                        "name": "PRICE",
                        "type": "DECIMAL",
                    },
                ],
                "identity": {
                    "fields": ["ID"],
                },
            },
        ],
        "constraints": [
            {
                "entity": "PRODUCT",
                "field": "PRICE",
                "operator": ">",
                "value": 0,
            },
        ],
    }

    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    assert not result.valid
    assert any(
        "constraint violated" in error
        for error in result.errors
    )


def test_validation_accepts_valid_foreign_key(
    tmp_path: Path,
) -> None:
    job_id = "JOB-5"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[
            {"ID": "1"},
            {"ID": "2"},
        ],
    )

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="ORDER",
        chunk_number=1,
        rows=[
            {"ID": "101", "CUSTOMER_ID": "1"},
            {"ID": "102", "CUSTOMER_ID": "2"},
        ],
    )

    specification = {
        "entities": [
            {
                "name": "CUSTOMER",
                "population": {"count": 2},
                "fields": [
                    {
                        "name": "ID",
                        "type": "INTEGER",
                    },
                ],
                "identity": {
                    "fields": ["ID"],
                },
            },
            {
                "name": "ORDER",
                "population": {"count": 2},
                "fields": [
                    {
                        "name": "ID",
                        "type": "INTEGER",
                    },
                    {
                        "name": "CUSTOMER_ID",
                        "type": "INTEGER",
                    },
                ],
                "identity": {
                    "fields": ["ID"],
                },
            },
        ],
        "foreign_keys": [
            {
                "name": "FK_ORDER_CUSTOMER",
                "source": {
                    "entity": "ORDER",
                    "fields": ["CUSTOMER_ID"],
                },
                "target": {
                    "entity": "CUSTOMER",
                    "fields": ["ID"],
                },
            },
        ],
    }

    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    assert result.valid
    assert result.errors == []


def test_validation_detects_orphan_foreign_key(
    tmp_path: Path,
) -> None:
    job_id = "JOB-6"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[
            {"ID": "1"},
        ],
    )

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="ORDER",
        chunk_number=1,
        rows=[
            {"ID": "101", "CUSTOMER_ID": "99"},
        ],
    )

    specification = {
        "entities": [
            {
                "name": "CUSTOMER",
                "population": {"count": 1},
                "fields": [
                    {
                        "name": "ID",
                        "type": "INTEGER",
                    },
                ],
                "identity": {
                    "fields": ["ID"],
                },
            },
            {
                "name": "ORDER",
                "population": {"count": 1},
                "fields": [
                    {
                        "name": "ID",
                        "type": "INTEGER",
                    },
                    {
                        "name": "CUSTOMER_ID",
                        "type": "INTEGER",
                    },
                ],
                "identity": {
                    "fields": ["ID"],
                },
            },
        ],
        "foreign_keys": [
            {
                "name": "FK_ORDER_CUSTOMER",
                "source": {
                    "entity": "ORDER",
                    "fields": ["CUSTOMER_ID"],
                },
                "target": {
                    "entity": "CUSTOMER",
                    "fields": ["ID"],
                },
            },
        ],
    }

    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    result = _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )

    assert not result.valid
    assert any(
        "references missing CUSTOMER key" in error
        for error in result.errors
    )
