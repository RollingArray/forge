from __future__ import annotations

import csv
import pytest
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
    rows: list[dict[str, str | None]],
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
    assert not result.valid
    assert any(
        "could not evaluate semantic unique" in error.lower()
        for error in result.errors
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
                "value": "0",
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
                "value": "0",
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


@pytest.mark.parametrize(
    ("actual", "operator", "expected"),
    [
        (
            "0.100000000000000001",
            "<",
            "0.100000000000000002",
        ),
        (
            "0.100000000000000002",
            ">",
            "0.100000000000000001",
        ),
    ],
)
def test_validation_compares_decimal_constraints_exactly(
    tmp_path: Path,
    actual: str,
    operator: str,
    expected: str,
) -> None:
    job_id = "DECIMAL-EXACT"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "PRICE": actual},
        ],
    )

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 1},
                "fields": [
                    {"name": "ID", "type": "INTEGER"},
                    {"name": "PRICE", "type": "DECIMAL"},
                ],
                "identity": {"fields": ["ID"]},
            },
        ],
        "constraints": [
            {
                "entity": "PRODUCT",
                "field": "PRICE",
                "operator": operator,
                "value": expected,
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


@pytest.mark.parametrize(
    "identity_value",
    ["", "   "],
    ids=["empty-identity", "whitespace-identity"],
)
def test_validation_rejects_blank_identity_components(
    tmp_path: Path,
    identity_value: str,
) -> None:
    job_id = "BLANK-IDENTITY"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[
            {"ID": identity_value},
        ],
    )

    specification = {
        "entities": [
            {
                "name": "CUSTOMER",
                "population": {"count": 1},
                "fields": [
                    {"name": "ID", "type": "STRING"},
                ],
                "identity": {"fields": ["ID"]},
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
        "identity contains a null or blank component" in error
        for error in result.errors
    )

    identity_metric = result.evidence.primary_keys["entities"]["CUSTOMER"]
    assert identity_metric["null_component_count"] == 1

    identity_rule = next(
        rule
        for rule in result.evidence.rule_results
        if rule["rule_id"] == "identity:CUSTOMER"
    )
    assert identity_rule["status"] == "FAILED"

def _run_foreign_key_nullability_case(
    *,
    tmp_path: Path,
    parent_fields: list[str],
    child_reference_fields: list[str],
    parent_rows: list[dict[str, str | None]],
    child_rows: list[dict[str, str | None]],
    child_participation: str,
):
    job_id = "JOB-FK-NULLABILITY"

    specification = {
        "entities": [
            {
                "name": "PARENT",
                "population": {"count": len(parent_rows)},
                "fields": [
                    {"name": field, "type": "INTEGER"}
                    for field in parent_fields
                ],
                "identity": {"fields": parent_fields},
            },
            {
                "name": "CHILD",
                "population": {"count": len(child_rows)},
                "fields": [
                    {"name": field, "type": "INTEGER"}
                    for field in ["ID", *child_reference_fields]
                ],
                "identity": {"fields": ["ID"]},
            },
        ],
        "foreign_keys": [
            {
                "name": "FK_CHILD_PARENT",
                "source": {
                    "entity": "CHILD",
                    "fields": child_reference_fields,
                },
                "target": {
                    "entity": "PARENT",
                    "fields": parent_fields,
                },
            },
        ],
        "relationships": [
            {
                "source": {
                    "entity": "CHILD",
                    "fields": child_reference_fields,
                },
                "target": {
                    "entity": "PARENT",
                    "fields": parent_fields,
                },
                "type": "MANY_TO_ONE",
                "source_participation": child_participation,
                "target_participation": "OPTIONAL",
            },
        ],
    }

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PARENT",
        chunk_number=1,
        rows=parent_rows,
    )
    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="CHILD",
        chunk_number=1,
        rows=child_rows,
    )
    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    return _validator(tmp_path).validate(
        specification=specification,
        data_model_id="TEST-MODEL",
        job_id=job_id,
    )


def test_validation_accepts_null_optional_single_column_foreign_key(
    tmp_path: Path,
) -> None:
    result = _run_foreign_key_nullability_case(
        tmp_path=tmp_path,
        parent_fields=["PARENT_ID"],
        child_reference_fields=["PARENT_REF"],
        parent_rows=[{"PARENT_ID": "1"}],
        child_rows=[{"ID": "101", "PARENT_REF": None}],
        child_participation="OPTIONAL",
    )

    assert result.valid
    assert result.errors == []


def test_validation_rejects_null_mandatory_single_column_foreign_key(
    tmp_path: Path,
) -> None:
    result = _run_foreign_key_nullability_case(
        tmp_path=tmp_path,
        parent_fields=["PARENT_ID"],
        child_reference_fields=["PARENT_REF"],
        parent_rows=[{"PARENT_ID": "1"}],
        child_rows=[{"ID": "101", "PARENT_REF": None}],
        child_participation="MANDATORY",
    )

    assert not result.valid
    assert any(
        "null or blank reference despite MANDATORY child participation"
        in error
        for error in result.errors
    )


def test_validation_accepts_fully_null_optional_composite_foreign_key(
    tmp_path: Path,
) -> None:
    result = _run_foreign_key_nullability_case(
        tmp_path=tmp_path,
        parent_fields=["PARENT_KEY_A", "PARENT_KEY_B"],
        child_reference_fields=["PARENT_REF_A", "PARENT_REF_B"],
        parent_rows=[{"PARENT_KEY_A": "1", "PARENT_KEY_B": "10"}],
        child_rows=[{
            "ID": "101",
            "PARENT_REF_A": None,
            "PARENT_REF_B": None,
        }],
        child_participation="OPTIONAL",
    )

    assert result.valid
    assert result.errors == []


def test_validation_rejects_partially_null_optional_composite_foreign_key(
    tmp_path: Path,
) -> None:
    result = _run_foreign_key_nullability_case(
        tmp_path=tmp_path,
        parent_fields=["PARENT_KEY_A", "PARENT_KEY_B"],
        child_reference_fields=["PARENT_REF_A", "PARENT_REF_B"],
        parent_rows=[{"PARENT_KEY_A": "1", "PARENT_KEY_B": "10"}],
        child_rows=[{
            "ID": "101",
            "PARENT_REF_A": "1",
            "PARENT_REF_B": None,
        }],
        child_participation="OPTIONAL",
    )

    assert not result.valid
    assert any(
        "partially null composite key" in error
        for error in result.errors
    )


@pytest.mark.parametrize(
    ("score", "expected_status", "expected_valid"),
    [
        ("0", "PASSED", True),
        ("100", "PASSED", True),
        ("-1", "FAILED", False),
        ("101", "FAILED", False),
    ],
    ids=[
        "minimum-boundary",
        "maximum-boundary",
        "below-minimum",
        "above-maximum",
    ],
)
def test_validation_enforces_inclusive_domain_bounds(
    tmp_path: Path,
    score: str,
    expected_status: str,
    expected_valid: bool,
) -> None:
    job_id = "DOMAIN-BOUNDS"

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 1},
                "fields": [
                    {"name": "ID", "type": "INTEGER"},
                    {
                        "name": "SCORE",
                        "type": "INTEGER",
                        "min": 0,
                        "max": 100,
                    },
                ],
                "identity": {"fields": ["ID"]},
            },
        ],
    }

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[{"ID": "1", "SCORE": score}],
    )
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

    rule = next(
        rule
        for rule in result.evidence.rule_results
        if rule["rule_id"] == "domain:PRODUCT.SCORE"
    )

    assert rule["status"] == expected_status
    assert rule["evaluated"] is (expected_status != "NOT_EVALUATED")
    assert result.valid is expected_valid


def test_validation_marks_invalid_domain_bound_not_evaluated(
    tmp_path: Path,
) -> None:
    job_id = "DOMAIN-INVALID-BOUND"

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 1},
                "fields": [
                    {"name": "ID", "type": "INTEGER"},
                    {
                        "name": "SCORE",
                        "type": "INTEGER",
                        "min": "not-an-integer",
                        "max": 100,
                    },
                ],
                "identity": {"fields": ["ID"]},
            },
        ],
    }

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[{"ID": "1", "SCORE": "50"}],
    )
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

    rule = next(
        rule
        for rule in result.evidence.rule_results
        if rule["rule_id"] == "domain:PRODUCT.SCORE"
    )

    assert rule["status"] == "NOT_EVALUATED"
    assert rule["evaluated"] is False
    assert rule["details"]["conversion_error_count"] == 1
    assert not result.valid
    assert any("domain rule conversion failed" in error for error in result.errors)


@pytest.mark.parametrize(
    ("field_type", "raw_value", "domain"),
    [
        ("INTEGER", "not-an-integer", {"min": 0, "max": 10}),
        ("DECIMAL", "not-a-decimal", {"min": "0", "max": "10"}),
        ("BOOLEAN", "not-a-boolean", {"allowed_values": [True, False]}),
    ],
    ids=["malformed-integer", "malformed-decimal", "malformed-boolean"],
)
def test_validation_reports_malformed_typed_artifact_values(
    tmp_path: Path,
    field_type: str,
    raw_value: str,
    domain: dict,
) -> None:
    job_id = f"MALFORMED-{field_type}"

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 1},
                "fields": [
                    {"name": "ID", "type": "INTEGER"},
                    {
                        "name": "VALUE",
                        "type": field_type,
                        **domain,
                    },
                ],
                "identity": {"fields": ["ID"]},
            },
        ],
    }

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[{"ID": "1", "VALUE": raw_value}],
    )
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

    rule = next(
        rule
        for rule in result.evidence.rule_results
        if rule["rule_id"] == "domain:PRODUCT.VALUE"
    )

    assert rule["status"] == "NOT_EVALUATED"
    assert rule["evaluated"] is False

    identity_rule = next(
        rule
        for rule in result.evidence.rule_results
        if rule["rule_id"] == "identity:PRODUCT"
    )
    assert identity_rule["status"] == "PASSED"
    assert identity_rule["details"]["conversion_error_count"] == 0

    assert len(result.evidence.conversion_errors) == 1
    conversion_error = result.evidence.conversion_errors[0]
    assert conversion_error["entity"] == "PRODUCT"
    assert conversion_error["row_number"] == 1
    assert conversion_error["field"] == "VALUE"
    assert conversion_error["field_type"] == field_type
    assert conversion_error["raw_value"] == raw_value

    assert not result.valid
    assert any("VALUE" in error for error in result.errors)


@pytest.mark.parametrize(
    ("field_type", "raw_value", "expected_error_type"),
    [
        ("INTEGER", "not-an-integer", "ValueError"),
        ("DECIMAL", "not-a-decimal", "ValueError"),
        ("BOOLEAN", "not-a-boolean", "ValueError"),
    ],
    ids=["integer", "decimal", "boolean"],
)
def test_typed_row_iterator_records_conversion_errors_and_continues(
    tmp_path: Path,
    field_type: str,
    raw_value: str,
    expected_error_type: str,
) -> None:
    job_id = f"ITERATOR-{field_type}"

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 2},
                "fields": [
                    {"name": "ID", "type": "INTEGER"},
                    {"name": "VALUE", "type": field_type},
                ],
                "identity": {"fields": ["ID"]},
            },
        ],
    }

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "VALUE": raw_value},
            {
                "ID": "2",
                "VALUE": "7" if field_type != "BOOLEAN" else "true",
            },
        ],
    )
    _commit_chunks(
        root=tmp_path,
        job_id=job_id,
        specification=specification,
    )

    validator = _validator(tmp_path)
    conversion_errors = {}

    rows = list(
        validator._iter_typed_rows(
            data_model_id="TEST-MODEL",
            job_id=job_id,
            entity_name="PRODUCT",
            field_types={
                "ID": "INTEGER",
                "VALUE": field_type,
            },
            conversion_errors=conversion_errors,
        )
    )

    assert len(rows) == 2
    assert rows[0]["ID"] == 1
    assert rows[0]["VALUE"] == raw_value
    assert rows[1]["ID"] == 2

    if field_type == "BOOLEAN":
        assert rows[1]["VALUE"] is True
    else:
        assert rows[1]["VALUE"] == 7

    error = conversion_errors[("PRODUCT", 1, "VALUE")]
    assert error["entity"] == "PRODUCT"
    assert error["row_number"] == 1
    assert error["field"] == "VALUE"
    assert error["field_type"] == field_type
    assert error["raw_value"] == raw_value
    assert error["error_type"] == expected_error_type
    assert error["error"]


def test_validation_marks_constraint_not_evaluated_for_malformed_value(
    tmp_path: Path,
) -> None:
    job_id = "CONSTRAINT-MALFORMED-VALUE"

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 1},
                "fields": [
                    {"name": "ID", "type": "INTEGER"},
                    {"name": "PRICE", "type": "INTEGER"},
                ],
                "identity": {"fields": ["ID"]},
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

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[{"ID": "1", "PRICE": "not-an-integer"}],
    )
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

    rule = next(
        rule
        for rule in result.evidence.rule_results
        if rule["category"] == "CONSTRAINT"
        and rule["details"]["entity"] == "PRODUCT"
        and rule["details"]["field"] == "PRICE"
    )

    assert rule["status"] == "NOT_EVALUATED"
    assert rule["evaluated"] is False
    assert rule["details"]["conversion_error_count"] == 1
    assert len(result.evidence.conversion_errors) == 1
    assert result.evidence.conversion_errors[0]["field"] == "PRICE"
    assert not result.valid


def test_semantic_unique_is_not_evaluated_for_malformed_value(
    tmp_path: Path,
) -> None:
    job_id = "SEM-UNIQUE-MALFORMED"

    specification = _semantic_unique_specification()
    specification["entities"][0]["population"]["count"] = 1
    specification["entities"][0]["fields"][1]["type"] = "INTEGER"

    _write_chunk(
        root=tmp_path,
        job_id=job_id,
        entity_name="PRODUCT",
        chunk_number=1,
        rows=[
            {"ID": "1", "DESCRIPTION": "not-an-integer"},
        ],
    )
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
    assert rule["evaluated"] is False
    assert rule["details"]["conversion_error_count"] == 1
    assert rule["details"]["evaluation_error"]
    assert len(result.evidence.conversion_errors) == 1
    assert result.evidence.conversion_errors[0]["field"] == "DESCRIPTION"
    assert not result.valid


@pytest.mark.parametrize(
    "malformed_endpoint",
    ["parent", "child"],
    ids=["malformed-parent-key", "malformed-child-key"],
)
def test_malformed_foreign_key_endpoint_is_not_evaluated(
    tmp_path: Path,
    malformed_endpoint: str,
) -> None:
    if malformed_endpoint == "parent":
        parent_rows = [
            {"PARENT_ID": "not-an-integer"},
            {"PARENT_ID": "1"},
        ]
        child_rows = [
            {"ID": "101", "PARENT_REF": "1"},
        ]
    else:
        parent_rows = [
            {"PARENT_ID": "1"},
        ]
        child_rows = [
            {"ID": "101", "PARENT_REF": "not-an-integer"},
        ]

    result = _run_foreign_key_nullability_case(
        tmp_path=tmp_path,
        parent_fields=["PARENT_ID"],
        child_reference_fields=["PARENT_REF"],
        parent_rows=parent_rows,
        child_rows=child_rows,
        child_participation="OPTIONAL",
    )

    foreign_key_rule = next(
        rule
        for rule in result.evidence.rule_results
        if rule["category"] == "FOREIGN_KEY"
    )
    relationship_rule = next(
        rule
        for rule in result.evidence.rule_results
        if rule["category"] == "RELATIONSHIP_CARDINALITY"
    )

    assert foreign_key_rule["status"] == "NOT_EVALUATED"
    assert foreign_key_rule["evaluated"] is False
    assert foreign_key_rule["details"]["conversion_error_count"] == 1
    assert foreign_key_rule["details"]["invalid_reference_count"] == 0

    assert relationship_rule["status"] == "NOT_EVALUATED"
    assert relationship_rule["evaluated"] is False
    assert relationship_rule["details"]["conversion_error_count"] == 1
    assert relationship_rule["details"]["dangling_reference_count"] == 0

    assert len(result.evidence.conversion_errors) == 1
    assert not result.valid
