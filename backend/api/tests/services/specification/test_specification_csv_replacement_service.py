import copy
import csv
import io
import json
import pytest
from pathlib import Path

from app.services.specification_csv_export_service import (
    SpecificationCsvExportService,
)
from app.services.specification_csv_replacement_service import (
    SpecificationCsvReplacementService,
)


def rich_specification():
    path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "validation_rich_specification.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_unchanged_export_converts_to_semantically_identical_specification():
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    candidate = result["specification"]

    assert candidate["entities"] == original["entities"]
    assert candidate["foreign_keys"] == original["foreign_keys"]
    assert candidate["relationships"] == original["relationships"]
    assert candidate["constraints"] == original["constraints"]


def test_preserves_unrepresented_top_level_sections():
    original = rich_specification()
    original["model"]["custom_metadata"] = {"owner": "FORGE"}
    original["generation"]["custom_setting"] = {"enabled": True}
    original["dependencies"] = [{"custom": "dependency"}]
    original["statistical_behavior"] = [{"custom": "behavior"}]
    original["scenarios"] = [{"custom": "scenario"}]

    csv_sections = SpecificationCsvExportService().export(original)
    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    candidate = result["specification"]
    assert candidate["model"] == original["model"]
    assert candidate["generation"] == original["generation"]
    assert candidate["dependencies"] == original["dependencies"]
    assert candidate["statistical_behavior"] == original["statistical_behavior"]
    assert candidate["scenarios"] == original["scenarios"]


def test_preserves_unrepresented_entity_and_field_metadata():
    original = rich_specification()
    original["entities"][0]["custom_entity_metadata"] = {"keep": True}
    original["entities"][0]["fields"][0]["custom_field_metadata"] = {
        "source": "manual"
    }

    csv_sections = SpecificationCsvExportService().export(original)
    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    customer = result["specification"]["entities"][0]
    assert customer["custom_entity_metadata"] == {"keep": True}
    assert customer["fields"][0]["custom_field_metadata"] == {
        "source": "manual"
    }


def test_deleted_entity_and_its_fields_are_removed():
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)

    entity_rows = csv_sections["entities"].splitlines()
    csv_sections["entities"] = "\n".join(
        [entity_rows[0]] + [
            row for row in entity_rows[1:]
            if not row.startswith("REGION,")
        ]
    ) + "\n"

    field_rows = csv_sections["fields_and_keys"].splitlines()
    csv_sections["fields_and_keys"] = "\n".join(
        [field_rows[0]] + [
            row for row in field_rows[1:]
            if not row.startswith("REGION,")
        ]
    ) + "\n"

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    names = [entity["name"] for entity in result["specification"]["entities"]]
    assert "REGION" not in names


def test_deleted_field_is_removed():
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)

    lines = csv_sections["fields_and_keys"].splitlines()
    csv_sections["fields_and_keys"] = "\n".join(
        [lines[0]] + [
            line for line in lines[1:]
            if not line.startswith("CUSTOMER,CUSTOMER_NAME,")
        ]
    ) + "\n"

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    customer = next(
        item for item in result["specification"]["entities"]
        if item["name"] == "CUSTOMER"
    )
    assert "CUSTOMER_NAME" not in {
        field["name"] for field in customer["fields"]
    }


def test_constraint_values_retain_json_types():
    original = rich_specification()
    original["constraints"] = [{
        "entity": "SALES_ORDER",
        "field": "TOTAL_AMOUNT",
        "operator": ">",
        "value": "12.50",
    }]

    csv_sections = SpecificationCsvExportService().export(original)
    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    assert result["specification"]["constraints"][0]["value"] == "12.50"


def test_relationship_endpoints_keep_their_json_representation():
    original = rich_specification()
    original["relationships"] = [{
        "source": {"entity": "CUSTOMER", "fields": ["CUSTOMER_ID"]},
        "target": "SALES_ORDER",
        "type": "ONE_TO_MANY",
        "source_participation": "OPTIONAL",
        "target_participation": "MANDATORY",
    }]

    csv_sections = SpecificationCsvExportService().export(original)
    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    relationship = result["specification"]["relationships"][0]
    assert relationship["source"] == {
        "entity": "CUSTOMER", "fields": ["CUSTOMER_ID"]
    }
    assert relationship["target"] == "SALES_ORDER"


def test_foreign_key_mappings_keep_order_and_names():
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    assert (
        result["specification"]["foreign_keys"]
        == original["foreign_keys"]
    )


def test_identity_field_order_is_reconstructed_from_positions():
    original = rich_specification()
    customer = original["entities"][0]
    customer["fields"].append({
        "name": "TENANT_ID",
        "type": "IDENTIFIER",
    })
    customer["identity"]["fields"] = ["TENANT_ID", "CUSTOMER_ID"]

    csv_sections = SpecificationCsvExportService().export(original)
    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    updated = result["specification"]["entities"][0]
    assert updated["identity"]["fields"] == ["TENANT_ID", "CUSTOMER_ID"]


def test_duplicate_field_rows_are_rejected():
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)
    lines = csv_sections["fields_and_keys"].splitlines()
    csv_sections["fields_and_keys"] += lines[1] + "\n"

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"]


def test_source_specification_is_not_mutated():
    original = rich_specification()
    before = copy.deepcopy(original)
    csv_sections = SpecificationCsvExportService().export(original)

    SpecificationCsvReplacementService().convert(csv_sections, original)

    assert original == before


def test_empty_sections_replace_existing_collections():
    original = rich_specification()
    exporter = SpecificationCsvExportService()
    csv_sections = exporter.export(original)

    for section in (
        "foreign_keys", "relationships", "constraints",
    ):
        headers = exporter.SECTION_HEADERS[section]
        csv_sections[section] = ",".join(headers) + "\n"

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    candidate = result["specification"]
    assert candidate["foreign_keys"] == []
    assert candidate["relationships"] == []
    assert candidate["constraints"] == []


def test_integer_generation_bounds_remain_integer_values():
    service = SpecificationCsvReplacementService()
    existing = {
        "entities": [{
            "name": "ITEM",
            "fields": [{
                "name": "QUANTITY",
                "type": "INTEGER",
                "generation": {
                    "parameters": {"minimum": 1, "maximum": 100}
                },
            }],
        }]
    }
    csv = SpecificationCsvExportService().export(existing)

    result = service.convert(csv, existing)

    assert result["issues"] == []
    parameters = result["specification"]["entities"][0]["fields"][0][
        "generation"
    ]["parameters"]
    assert parameters["minimum"] == 1
    assert parameters["maximum"] == 100
    assert isinstance(parameters["minimum"], int)
    assert isinstance(parameters["maximum"], int)


def test_unexposed_generation_parameters_survive_csv_replacement():
    service = SpecificationCsvReplacementService()
    existing = {
        "entities": [{
            "name": "ITEM",
            "fields": [{
                "name": "PRICE",
                "type": "DECIMAL",
                "generation": {
                    "strategy": "RANDOM",
                    "parameters": {
                        "minimum": "0.000000000000000001",
                        "maximum": "999999999999.999999",
                        "precision": 18,
                        "scale": 6,
                        "custom_parameter": {"enabled": True},
                    },
                },
            }],
        }]
    }

    csv_sections = SpecificationCsvExportService().export(existing)
    headers = csv_sections["fields_and_keys"].splitlines()[0].split(",")
    assert len(headers) == 17
    assert "precision" not in headers
    assert "scale" not in headers
    assert "generation_parameters" not in headers

    result = service.convert(csv_sections, existing)

    assert result["issues"] == []
    parameters = result["specification"]["entities"][0]["fields"][0][
        "generation"
    ]["parameters"]

    assert parameters["minimum"] == "0.000000000000000001"
    assert parameters["maximum"] == "999999999999.999999"
    assert parameters["precision"] == 18
    assert parameters["scale"] == 6
    assert parameters["custom_parameter"] == {"enabled": True}



def test_matching_foreign_key_relationship_and_constraint_keep_metadata():
    service = SpecificationCsvReplacementService()
    existing = {
        "entities": [{
            "name": "ITEM",
            "fields": [{"name": "ITEM_ID", "type": "INTEGER"}],
        }],
        "foreign_keys": [{
            "name": "FK_ITEM",
            "source": {"entity": "ITEM", "fields": ["ITEM_ID"]},
            "target": {"entity": "ITEM", "fields": ["ITEM_ID"]},
            "custom_metadata": {"owner": "domain-team"},
        }],
        "relationships": [{
            "source": "ITEM",
            "target": "ITEM",
            "type": "ONE_TO_ONE",
            "source_participation": "MANDATORY",
            "target_participation": "MANDATORY",
            "custom_metadata": {"origin": "architecture-review"},
        }],
        "constraints": [{
            "entity": "ITEM",
            "field": "ITEM_ID",
            "operator": ">",
            "value": 0,
            "custom_metadata": {"rule_id": "RULE-001"},
        }],
    }
    csv = SpecificationCsvExportService().export(existing)

    result = service.convert(csv, existing)

    assert result["issues"] == []
    candidate = result["specification"]
    assert candidate["foreign_keys"][0]["custom_metadata"] == {
        "owner": "domain-team"
    }
    assert candidate["relationships"][0]["custom_metadata"] == {
        "origin": "architecture-review"
    }
    assert candidate["constraints"][0]["custom_metadata"] == {
        "rule_id": "RULE-001"
    }


def test_metadata_survives_replacement_and_constraint_edit():
    import csv
    import io

    exporter = SpecificationCsvExportService()
    service = SpecificationCsvReplacementService()

    original = {
        "entities": [{
            "name": "ITEM",
            "fields": [{"name": "ITEM_ID", "type": "INTEGER"}],
        }],
        "foreign_keys": [{
            "name": "FK_ITEM",
            "source": {
                "entity": "ITEM",
                "fields": ["ITEM_ID"],
                "custom_source_metadata": {"origin": "source"},
            },
            "target": {
                "entity": "ITEM",
                "fields": ["ITEM_ID"],
                "custom_target_metadata": {"origin": "target"},
            },
            "custom_record_metadata": {"owner": "domain-team"},
        }],
        "relationships": [{
            "source": "ITEM",
            "target": "ITEM",
            "type": "ONE_TO_ONE",
            "source_participation": "MANDATORY",
            "target_participation": "MANDATORY",
            "custom_relationship_metadata": {"reviewed": True},
        }],
        "constraints": [{
            "entity": "ITEM",
            "field": "ITEM_ID",
            "operator": ">",
            "value": 0,
            "custom_constraint_metadata": {"rule_id": "RULE-001"},
        }],
    }

    sections = exporter.export(original)

    def edit_csv(content, changes):
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        for row in rows:
            row.update(changes)
        output = io.StringIO(newline="")
        writer = csv.DictWriter(
            output,
            fieldnames=reader.fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    sections["constraints"] = edit_csv(
        sections["constraints"],
        {"value": "5"},
    )

    result = service.convert(sections, original)

    assert result["issues"] == []
    candidate = result["specification"]

    foreign_key = candidate["foreign_keys"][0]
    assert foreign_key["source"]["fields"] == ["ITEM_ID"]
    assert foreign_key["source"]["custom_source_metadata"] == {
        "origin": "source"
    }
    assert foreign_key["target"]["custom_target_metadata"] == {
        "origin": "target"
    }
    assert foreign_key["custom_record_metadata"] == {
        "owner": "domain-team"
    }

    relationship = candidate["relationships"][0]
    assert relationship["type"] == "ONE_TO_ONE"
    assert relationship["custom_relationship_metadata"] == {
        "reviewed": True
    }

    constraint = candidate["constraints"][0]
    assert constraint["value"] == 5
    assert constraint["custom_constraint_metadata"] == {
        "rule_id": "RULE-001"
    }


def test_field_conversion_does_not_add_temporary_properties_to_entities():
    original = {
        "entities": [{
            "name": "ITEM",
            "fields": [{
                "name": "ITEM_ID",
                "type": "INTEGER",
                "custom_field_metadata": {"source": "original"},
            }],
            "custom_entity_metadata": {"owner": "engineering"},
        }],
        "foreign_keys": [],
        "relationships": [],
        "constraints": [],
    }

    sections = SpecificationCsvExportService().export(original)
    result = SpecificationCsvReplacementService().convert(sections, original)

    assert result["issues"] == []
    entity = result["specification"]["entities"][0]
    assert "_replacement_old_fields" not in entity
    assert entity["custom_entity_metadata"] == {"owner": "engineering"}
    assert entity["fields"][0]["custom_field_metadata"] == {
        "source": "original"
    }


def test_replacement_supports_new_entity_with_multiple_fields():
    """New entities must accept fields without an existing metadata baseline."""
    import copy
    import csv
    import io

    from app.services.specification_csv_export_service import (
        SpecificationCsvExportService,
    )
    from app.services.specification_csv_replacement_service import (
        SpecificationCsvReplacementService,
    )

    original = {
        "version": "1.0",
        "model": {"name": "Empty Model", "description": ""},
        "generation": {"seed": 42, "scenario": "NORMAL"},
        "entities": [],
        "foreign_keys": [],
        "relationships": [],
        "constraints": [],
        "dependencies": [],
        "statistical_behavior": [],
        "scenarios": [],
    }
    original_snapshot = copy.deepcopy(original)

    headers = SpecificationCsvExportService.SECTION_HEADERS

    def make_csv(section, rows):
        output = io.StringIO(newline="")
        writer = csv.DictWriter(
            output,
            fieldnames=headers[section],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    csv_sections = {
        "entities": make_csv("entities", [{
            "entity": "NEW_CUSTOMER",
            "description": "New customer entity",
            "population_count": "100",
            "population_scaling": "FIXED",
        }]),
        "fields_and_keys": make_csv("fields_and_keys", [
            {
                "entity": "NEW_CUSTOMER",
                "field": "CUSTOMER_ID",
                "type": "INTEGER",
            },
            {
                "entity": "NEW_CUSTOMER",
                "field": "CUSTOMER_NAME",
                "type": "STRING",
            },
        ]),
        "foreign_keys": make_csv("foreign_keys", []),
        "relationships": make_csv("relationships", []),
        "constraints": make_csv("constraints", []),
    }

    result = SpecificationCsvReplacementService().convert(
        csv_sections=csv_sections,
        existing_specification=original,
    )

    assert result["issues"] == []
    assert result["specification"] is not None

    entities = result["specification"]["entities"]
    assert len(entities) == 1
    assert entities[0]["name"] == "NEW_CUSTOMER"

    fields = entities[0]["fields"]
    assert [field["name"] for field in fields] == [
        "CUSTOMER_ID",
        "CUSTOMER_NAME",
    ]

    assert fields[0]["type"] == "INTEGER"
    assert fields[1]["type"] == "STRING"

    # Conversion must never mutate the original specification.
    assert original == original_snapshot


def test_decimal_constraint_values_remain_strings_on_replacement():
    original = rich_specification()
    original["constraints"] = [{
        "entity": "SALES_ORDER",
        "field": "TOTAL_AMOUNT",
        "operator": ">",
        "value": 12.5,
    }]

    csv_sections = SpecificationCsvExportService().export(original)
    csv_sections["constraints"] = (
        "entity,field,operator,value\n"
        "SALES_ORDER,TOTAL_AMOUNT,>,0.0500\n"
    )

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    assert result["specification"]["constraints"][0]["value"] == "0.0500"
    assert isinstance(
        result["specification"]["constraints"][0]["value"], str
    )


def test_new_decimal_constraint_values_remain_strings():
    original = rich_specification()
    original["constraints"] = []

    csv_sections = SpecificationCsvExportService().export(original)
    csv_sections["constraints"] = (
        "entity,field,operator,value\n"
        "SALES_ORDER,TOTAL_AMOUNT,>,0.0500\n"
    )

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    assert result["specification"]["constraints"][0]["value"] == "0.0500"
    assert isinstance(
        result["specification"]["constraints"][0]["value"], str
    )


@pytest.mark.parametrize(
    "existing_value",
    ["new", None, 12.5],
)
def test_blank_decimal_constraint_values_become_none(existing_value):
    original = rich_specification()

    if existing_value != "new":
        original["constraints"] = [{
            "entity": "SALES_ORDER",
            "field": "TOTAL_AMOUNT",
            "operator": ">",
            "value": existing_value,
        }]
    else:
        original["constraints"] = []

    csv_sections = SpecificationCsvExportService().export(original)
    csv_sections["constraints"] = (
        "entity,field,operator,value\n"
        "SALES_ORDER,TOTAL_AMOUNT,>,   \n"
    )

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["issues"] == []
    assert result["specification"]["constraints"][0]["value"] is None


def test_invalid_entity_population_count_reports_structured_csv_location():
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)

    rows = list(csv.reader(io.StringIO(csv_sections["entities"])))
    population_column = rows[0].index("population_count")
    rows[1][population_column] = "not-a-number"

    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    csv_sections["entities"] = output.getvalue()

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"] == [{
        "section": "entities",
        "row": 2,
        "column": "population_count",
        "message": "population_count must be a whole number.",
    }]


@pytest.mark.parametrize(
    ("section", "column", "replacement", "expected_section", "message"),
    [
        (
            "entities",
            "population_scaling",
            "INVALID",
            "entities",
            "population_scaling must be FIXED or SCALABLE.",
        ),
        (
            "fields_and_keys",
            "identity_position",
            "not-a-number",
            "fields_and_keys",
            "identity_position must be a positive whole number.",
        ),
        (
            "fields_and_keys",
            "identity_position",
            "0",
            "fields_and_keys",
            "identity_position must be at least 1.",
        ),
    ],
)
def test_row_conversion_errors_report_structured_csv_locations(
    section,
    column,
    replacement,
    expected_section,
    message,
):
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)

    rows = list(csv.reader(io.StringIO(csv_sections[section])))
    column_index = rows[0].index(column)
    rows[1][column_index] = replacement

    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    csv_sections[section] = output.getvalue()

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"] == [{
        "section": expected_section,
        "row": 2,
        "column": column,
        "message": message,
    }]

@pytest.mark.parametrize(
    ("field_name", "column", "replacement", "message"),
    [
        (
            "CUSTOMER_STATUS",
            "values",
            "{invalid-json",
            "values must be valid JSON.",
        ),
        (
            "CUSTOMER_STATUS",
            "values",
            '{"status": "ACTIVE"}',
            "values must be a JSON array.",
        ),
        (
            "CUSTOMER_NAME",
            "minimum_length",
            "not-a-number",
            "minimum_length must be an integer.",
        ),
        (
            "CUSTOMER_NAME",
            "maximum_length",
            "1.5",
            "maximum_length must be an integer.",
        ),
        (
            "QUANTITY",
            "minimum",
            "not-a-number",
            "minimum must be a whole number for INTEGER fields.",
        ),
    ],
)
def test_generation_conversion_errors_report_structured_csv_locations(
    field_name,
    column,
    replacement,
    message,
):
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)

    rows = list(csv.reader(io.StringIO(csv_sections["fields_and_keys"])))
    headers = rows[0]
    field_column = headers.index("field")
    target_column = headers.index(column)

    matching_rows = [
        row for row in rows[1:] if row[field_column] == field_name
    ]
    assert len(matching_rows) == 1

    target_row = matching_rows[0]
    target_row[target_column] = replacement
    expected_row_number = rows.index(target_row) + 1

    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    csv_sections["fields_and_keys"] = output.getvalue()

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"] == [{
        "section": "fields_and_keys",
        "row": expected_row_number,
        "column": column,
        "message": message,
    }]

@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        (
            "{invalid-json",
            "source_fields must contain valid JSON.",
        ),
        (
            '{"field": "CUSTOMER_ID"}',
            "source_fields must be a non-empty JSON array of field names.",
        ),
        (
            "[]",
            "source_fields must be a non-empty JSON array of field names.",
        ),
    ],
)
def test_foreign_key_source_fields_errors_report_structured_csv_locations(
    replacement,
    message,
):
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)

    rows = list(csv.reader(io.StringIO(csv_sections["foreign_keys"])))
    headers = rows[0]
    source_fields_column = headers.index("source_fields")

    assert len(rows) > 1, "Expected the fixture to contain a foreign-key row."
    rows[1][source_fields_column] = replacement

    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    csv_sections["foreign_keys"] = output.getvalue()

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"] == [{
        "section": "foreign_keys",
        "row": 2,
        "column": "source_fields",
        "message": message,
    }]

@pytest.mark.parametrize(
    ("column", "replacement"),
    [
        ("source_entity", "UNKNOWN_SOURCE"),
        ("target_entity", "UNKNOWN_TARGET"),
    ],
)
def test_foreign_key_unknown_entities_report_structured_csv_locations(
    column,
    replacement,
):
    original = rich_specification()
    csv_sections = SpecificationCsvExportService().export(original)

    rows = list(csv.reader(io.StringIO(csv_sections["foreign_keys"])))
    headers = rows[0]
    target_column = headers.index(column)

    assert len(rows) > 1, "Expected the fixture to contain a foreign-key row."
    rows[1][target_column] = replacement

    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    csv_sections["foreign_keys"] = output.getvalue()

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"] == [{
        "section": "foreign_keys",
        "row": 2,
        "column": column,
        "message": (
            "unknown source or target entity "
            f"({replacement!r}, "
            f"{rows[1][headers.index('target_entity')]!r})."
            if column == "source_entity"
            else
            "unknown source or target entity "
            f"({rows[1][headers.index('source_entity')]!r}, "
            f"{replacement!r})."
        ),
    }]


def test_deleted_entity_keeps_existing_foreign_key_skip_behavior():
    original = rich_specification()
    existing_foreign_key = original["foreign_keys"][0]
    source = existing_foreign_key["source"]
    target = existing_foreign_key["target"]

    remaining_entities = [
        entity
        for entity in original["entities"]
        if entity["name"] != target["entity"]
    ]

    parsed = {
        "rows": [{
            "row_number": 2,
            "values": {
                "source_entity": source["entity"],
                "source_fields": (
                    "[" + ", ".join(f'"{field}"' for field in source["fields"]) + "]"
                ),
                "target_entity": target["entity"],
            },
        }],
    }

    result = SpecificationCsvReplacementService()._convert_foreign_keys(
        parsed,
        remaining_entities,
        original["foreign_keys"],
    )

    assert result == []

def test_foreign_key_multiple_legacy_matches_report_structured_csv_location():
    import copy

    original = rich_specification()
    original["foreign_keys"].append(
        copy.deepcopy(original["foreign_keys"][0])
    )
    csv_sections = SpecificationCsvExportService().export(original)

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"] == [{
        "section": "foreign_keys",
        "row": 2,
        "column": "source_fields",
        "message": (
            "multiple existing foreign keys match this legacy declaration. "
            "The original CSV format cannot distinguish them."
        ),
    }]


def test_foreign_key_incompatible_target_mapping_reports_structured_location():
    import copy

    original = rich_specification()
    foreign_key = original["foreign_keys"][0]
    source = foreign_key["source"]
    target = foreign_key["target"]

    entities = copy.deepcopy(original["entities"])
    existing = copy.deepcopy(original["foreign_keys"])

    target_entity = next(
        entity for entity in entities
        if entity["name"] == target["entity"]
    )
    target_entity["identity"]["fields"] = ["TARGET_A", "TARGET_B"]
    existing[0]["target"]["fields"] = ["TARGET_A", "TARGET_B"]

    parsed = {
        "rows": [{
            "row_number": 2,
            "values": {
                "source_entity": source["entity"],
                "source_fields": (
                    "[" + ", ".join(f'"{field}"' for field in source["fields"]) + "]"
                ),
                "target_entity": target["entity"],
            },
        }],
    }

    with pytest.raises(ValueError) as exc_info:
        SpecificationCsvReplacementService()._convert_foreign_keys(
            parsed,
            entities,
            existing,
        )

    assert exc_info.value.section == "foreign_keys"
    assert exc_info.value.row == 2
    assert exc_info.value.column == "target_entity"
    assert str(exc_info.value) == (
        f"cannot derive a compatible target-field mapping for "
        f"{target['entity']!r}. The target identity and existing FK "
        "mapping do not provide a matching number of fields."
    )

def _parsed_relationship_row(
    source_entity,
    target_entity,
    relationship_type,
    source_participation="MANDATORY",
    target_participation="MANDATORY",
):
    return {
        "rows": [{
            "row_number": 2,
            "values": {
                "source_entity": source_entity,
                "target_entity": target_entity,
                "type": relationship_type,
                "source_participation": source_participation,
                "target_participation": target_participation,
            },
        }],
    }


def test_relationship_duplicate_unchanged_matches_report_structured_location():
    import copy

    original = rich_specification()
    existing = copy.deepcopy(original["relationships"])
    existing.append(copy.deepcopy(existing[0]))

    row = existing[0]
    parsed = _parsed_relationship_row(
        row["source"],
        row["target"],
        row["type"],
        row["source_participation"],
        row["target_participation"],
    )

    with pytest.raises(ValueError) as exc_info:
        SpecificationCsvReplacementService()._convert_relationships(
            parsed,
            original["foreign_keys"],
            existing,
        )

    assert exc_info.value.section == "relationships"
    assert exc_info.value.row == 2
    assert exc_info.value.column == "type"
    assert str(exc_info.value) == (
        "multiple existing relationships match this declaration."
    )


def test_relationship_unsupported_type_reports_structured_location():
    original = rich_specification()
    parsed = _parsed_relationship_row(
        "PRODUCT",
        "WAREHOUSE",
        "MANY_TO_MANY",
        "MANDATORY",
        "OPTIONAL",
    )

    with pytest.raises(ValueError) as exc_info:
        SpecificationCsvReplacementService()._convert_relationships(
            parsed,
            original["foreign_keys"],
            original["relationships"],
        )

    assert exc_info.value.section == "relationships"
    assert exc_info.value.row == 2
    assert exc_info.value.column == "type"
    assert str(exc_info.value) == (
        "unsupported relationship type 'MANY_TO_MANY'. "
        "A new or edited relationship of this type cannot be "
        "reconstructed from the original CSV format."
    )


def test_relationship_missing_mapping_reports_structured_location():
    original = rich_specification()
    parsed = _parsed_relationship_row(
        "CUSTOMER",
        "PRODUCT",
        "ONE_TO_MANY",
    )

    with pytest.raises(ValueError) as exc_info:
        SpecificationCsvReplacementService()._convert_relationships(
            parsed,
            original["foreign_keys"],
            [],
        )

    assert exc_info.value.section == "relationships"
    assert exc_info.value.row == 2
    assert exc_info.value.column == "source_entity"
    assert str(exc_info.value) == (
        "no complete ordered foreign-key mapping supports "
        "CUSTOMER -> PRODUCT (ONE_TO_MANY)."
    )

@pytest.mark.parametrize(
    ("existing_value", "replacement", "message"),
    [
        (True, "not-a-boolean", "value must be true or false."),
        (42, "not-an-integer", "value must be an integer."),
        (12.5, "not-a-number", "value must be numeric."),
    ],
)
def test_constraint_conversion_errors_report_structured_csv_locations(
    existing_value,
    replacement,
    message,
):
    original = {
        "entities": [{
            "name": "ITEM",
            "fields": [{"name": "ITEM_VALUE", "type": "STRING"}],
        }],
        "foreign_keys": [],
        "relationships": [],
        "constraints": [{
            "entity": "ITEM",
            "field": "ITEM_VALUE",
            "operator": ">",
            "value": existing_value,
        }],
    }

    csv_sections = SpecificationCsvExportService().export(original)
    csv_sections["constraints"] = (
        "entity,field,operator,value\n"
        f"ITEM,ITEM_VALUE,>,{replacement}\n"
    )

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"] == [{
        "section": "constraints",
        "row": 2,
        "column": "value",
        "message": message,
    }]


def test_constraint_duplicate_matches_report_structured_csv_location():
    import copy

    original = {
        "entities": [{
            "name": "ITEM",
            "fields": [{"name": "ITEM_VALUE", "type": "STRING"}],
        }],
        "foreign_keys": [],
        "relationships": [],
        "constraints": [{
            "entity": "ITEM",
            "field": "ITEM_VALUE",
            "operator": ">",
            "value": "10",
        }],
    }
    original["constraints"].append(
        copy.deepcopy(original["constraints"][0])
    )

    csv_sections = SpecificationCsvExportService().export(original)

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"] == [{
        "section": "constraints",
        "row": 2,
        "column": "operator",
        "message": (
            "multiple existing constraints match this entity, "
            "field and operator."
        ),
    }]

@pytest.mark.parametrize(
    ("second_position", "message"),
    [
        (
            "1",
            "duplicate identity_position 1 for entity 'ITEM'.",
        ),
        (
            "3",
            "identity_position values must be contiguous starting at 1.",
        ),
    ],
)
def test_identity_position_errors_report_structured_csv_locations(
    second_position,
    message,
):
    original = {
        "entities": [{
            "name": "ITEM",
            "fields": [
                {"name": "ITEM_ID", "type": "INTEGER"},
                {"name": "TENANT_ID", "type": "INTEGER"},
            ],
            "identity": {"fields": ["ITEM_ID", "TENANT_ID"]},
        }],
        "foreign_keys": [],
        "relationships": [],
        "constraints": [],
    }

    csv_sections = SpecificationCsvExportService().export(original)
    rows = list(csv.reader(io.StringIO(csv_sections["fields_and_keys"])))
    position_column = rows[0].index("identity_position")
    rows[2][position_column] = second_position

    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    csv_sections["fields_and_keys"] = output.getvalue()

    result = SpecificationCsvReplacementService().convert(
        csv_sections, original
    )

    assert result["specification"] is None
    assert result["issues"] == [{
        "section": "fields_and_keys",
        "row": 3,
        "column": "identity_position",
        "message": message,
    }]
