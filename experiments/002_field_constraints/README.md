# Experiment 002: Field Constraint-Controlled Generation

**Status:** Completed  
**Experiment Type:** Structural  
**FORGE Area:** Specification / Generation  
**Objective:** Determine whether explicit field-level constraints can control the structure and validity of generated synthetic data without requiring real data.

---

## 1. Research Question

Can synthetic data generation reliably enforce structural constraints defined in metadata, such as:

- Field length
- Numeric precision
- Allowed values
- Value format
- Nullability
- Data type
- Identifier formatting

without requiring access to real production data?

---

## 2. Hypothesis

A synthetic data generator can produce structurally valid values when
field constraints are explicitly defined as part of the generation
metadata.

The generator should be able to use metadata to ensure that generated
values conform to the declared structural constraints.

The experiment should demonstrate that:

> **The structure of a dataset can be specified independently from the
> data used to populate it.**

The generated values do not need to resemble real-world values at this
stage.

The purpose of this experiment is to determine whether **field-level
constraints can become explicit generation instructions** rather than
implicit assumptions inside the generator.

---

## 3. Scope

This experiment will generate a small synthetic dataset for a single
generic entity.

The experiment will build on the metadata-only generation capability
established in Experiment 001.

### Included

- Entity definition
- Field definition
- String fields
- Numeric fields
- Boolean fields
- Date fields
- Field length constraints
- Numeric precision
- Allowed value constraints
- Nullability
- Identifier formatting
- Configurable record volume
- Deterministic generation where practical
- Structural validation
- Generation output

### Excluded

- Real production data
- Machine Learning
- Deep Learning
- Large Language Models
- Statistical inference
- Distribution modelling
- Cross-field relationships
- Cross-entity relationships
- Complex business rules
- Domain-specific SAP, PLM, MES or ERP logic
- Advanced statistical validation

These capabilities will be explored in later experiments.

---

## 4. Initial Entity

The experiment will use a generic `CUSTOMER` entity.

Example fields:

| Field | Type | Constraint |
|---|---|---|
| CUSTOMER_ID | string | 10 characters, fixed-width identifier |
| COUNTRY | string | 2 characters, allowed values |
| AGE | integer | 0–100 |
| CUSTOMER_TYPE | string | Allowed categorical values |
| ACTIVE | boolean | True / False |
| CREATED_DATE | date | Valid date format |
| PHONE | string | Optional, fixed length |

The entity is intentionally domain-neutral.

---

## 5. Experiment Configuration

The generation behavior will be defined through metadata rather than
hard-coded field-specific logic.

Example:

```python
{
    "entity": "CUSTOMER",
    "fields": {
        "CUSTOMER_ID": {
            "type": "string",
            "semantic": "identifier",
            "length": 10,
            "required": True
        },
        "COUNTRY": {
            "type": "string",
            "length": 2,
            "allowed_values": ["US", "DE", "FR", "IN"],
            "required": True
        },
        "AGE": {
            "type": "integer",
            "min": 0,
            "max": 100,
            "required": True
        },
        "CUSTOMER_TYPE": {
            "type": "string",
            "allowed_values": [
                "BUSINESS",
                "INDIVIDUAL"
            ],
            "required": True
        },
        "ACTIVE": {
            "type": "boolean",
            "required": True
        },
        "CREATED_DATE": {
            "type": "date",
            "required": True
        },
        "PHONE": {
            "type": "string",
            "length": 10,
            "required": False
        }
    }
}