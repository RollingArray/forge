import csv
import io
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.services.specification_csv_export_service import (
    SpecificationCsvExportService,
)


@pytest.fixture
def service():
    return SpecificationCsvExportService()


@pytest.fixture
def rich_specification():
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "validation_rich_specification.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def read_rows(csv_text):
    return list(csv.DictReader(io.StringIO(csv_text)))


def test_exports_all_five_sections_and_headers(service, rich_specification):
    exported = service.export(rich_specification)

    assert set(exported) == {
        "entities",
        "fields_and_keys",
        "foreign_keys",
        "relationships",
        "constraints",
    }

    for section, headers in service.SECTION_HEADERS.items():
        reader = csv.reader(io.StringIO(exported[section]))
        assert tuple(next(reader)) == headers


def test_exports_entity_population_and_identity(service, rich_specification):
    exported = service.export(rich_specification)

    entity_rows = read_rows(exported["entities"])
    assert entity_rows

    field_rows = read_rows(exported["fields_and_keys"])
    assert field_rows

    identity_rows = [
        row for row in field_rows if row["identity_position"]
    ]
    assert identity_rows


def test_exports_original_foreign_key_columns_and_ordered_mappings(
    service, rich_specification
):
    exported = service.export(rich_specification)
    rows = read_rows(exported["foreign_keys"])

    assert rows
    original = rich_specification["foreign_keys"][0]

    matching = next(
        row for row in rows
        if row["source_entity"] == original["source"]["entity"]
        and row["target_entity"] == original["target"]["entity"]
        and json.loads(row["source_fields"]) == original["source"]["fields"]
    )

    assert set(matching) == {
        "source_entity", "source_fields", "target_entity"
    }


def test_exports_relationships_using_original_entity_columns(
    service, rich_specification
):
    specification = deepcopy(rich_specification)
    specification["relationships"].append({
        "source": {"entity": "CUSTOMER", "fields": ["CUSTOMER_ID"]},
        "target": "ORDER",
        "type": "ONE_TO_MANY",
        "source_participation": "ONE",
        "target_participation": "MANY",
    })

    exported = service.export(specification)
    rows = read_rows(exported["relationships"])

    matching = next(
        row for row in rows
        if row["source_entity"] == "CUSTOMER"
        and row["target_entity"] == "ORDER"
        and row["type"] == "ONE_TO_MANY"
    )

    assert matching == {
        "source_entity": "CUSTOMER",
        "target_entity": "ORDER",
        "type": "ONE_TO_MANY",
        "source_participation": "ONE",
        "target_participation": "MANY",
    }


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0"),
        (12.5, "12.5"),
        ("0", "0"),
        (True, "True"),
        (False, "False"),
        (None, ""),
    ],
)
def test_exports_scalar_constraint_values(
    service, rich_specification, value, expected
):
    specification = deepcopy(rich_specification)
    specification["constraints"] = [{
        "entity": "CUSTOMER",
        "field": "CUSTOMER_ID",
        "operator": "EQUALS",
        "value": value,
    }]

    exported = service.export(specification)
    rows = read_rows(exported["constraints"])

    assert rows[0] == {
        "entity": "CUSTOMER",
        "field": "CUSTOMER_ID",
        "operator": "EQUALS",
        "value": expected,
    }


@pytest.mark.parametrize("value", [["A", "B"], {"minimum": 1}])
def test_rejects_non_scalar_constraint_values(
    service, rich_specification, value
):
    specification = deepcopy(rich_specification)
    specification["constraints"] = [{
        "entity": "CUSTOMER",
        "field": "CUSTOMER_ID",
        "operator": "EQUALS",
        "value": value,
    }]

    with pytest.raises(ValueError, match="cannot be represented"):
        service.export(specification)


def test_exports_original_17_field_columns(service):
    specification = {
        "entities": [{
            "name": "CUSTOMER",
            "fields": [{
                "name": "CUSTOMER_NAME",
                "type": "STRING",
                "generation": {
                    "strategy": "RANDOM",
                    "distribution": "UNIFORM",
                    "generator": "STRING",
                    "parameters": {
                        "minimum_length": 2,
                        "maximum_length": 40,
                        "custom_parameter": {"enabled": True},
                    },
                },
            }],
        }]
    }

    exported = service.export(specification)
    reader = csv.DictReader(io.StringIO(exported["fields_and_keys"]))
    assert len(reader.fieldnames) == 17
    assert reader.fieldnames == [
        "entity", "field", "type", "identity_position",
        "identity_strategy", "generation_strategy", "distribution",
        "generator", "minimum", "maximum", "minimum_length",
        "maximum_length", "character_set", "pattern",
        "semantic_description", "semantic_mode", "values",
    ]

    row = next(reader)
    assert row["minimum_length"] == "2"
    assert row["maximum_length"] == "40"
    assert "precision" not in row
    assert "scale" not in row
    assert "generation_parameters" not in row


def test_empty_sections_still_export_headers(service):
    exported = service.export({})

    for section, headers in service.SECTION_HEADERS.items():
        reader = csv.reader(io.StringIO(exported[section]))
        assert tuple(next(reader)) == headers
        assert list(reader) == []


def test_export_does_not_mutate_specification(service, rich_specification):
    original = deepcopy(rich_specification)

    service.export(rich_specification)

    assert rich_specification == original


def test_csv_escaping_preserves_commas_quotes_and_newlines(service):
    specification = {
        "entities": [{
            "name": "CUSTOMER",
            "description": 'Customer, "primary"\nrecord',
            "population": {"count": 10},
            "fields": [],
        }]
    }

    exported = service.export(specification)
    rows = read_rows(exported["entities"])

    assert rows[0]["description"] == 'Customer, "primary"\nrecord'


def test_rejects_non_object_specification(service):
    with pytest.raises(ValueError, match="JSON object"):
        service.export([])


def test_rejects_non_list_section(service):
    with pytest.raises(ValueError, match="must be a list"):
        service.export({"entities": {"name": "CUSTOMER"}})


def test_rejects_non_object_section_item(service):
    with pytest.raises(ValueError, match="must be an object"):
        service.export({"entities": ["CUSTOMER"]})
