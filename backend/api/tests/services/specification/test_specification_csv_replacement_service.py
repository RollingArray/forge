import copy
import json
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
