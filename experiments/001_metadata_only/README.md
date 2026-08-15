# Experiment 001: Metadata-Only Generation

**Status:** Planned  
**Experiment Type:** Foundational  
**FORGE Area:** Specification / Generation  
**Objective:** Determine the minimum metadata required to generate synthetic data without access to real data.

---

## 1. Research Question

Can a useful synthetic dataset be generated using only a structured description of the data system, without using real production data?

---

## 2. Hypothesis

A meaningful first-generation synthetic dataset can be produced from metadata describing:

- Entity
- Field
- Data type
- Field semantics
- Format
- Domain or value constraints
- Optionality

The generated data does not need to reproduce the statistical characteristics of a real dataset at this stage.

The purpose of this experiment is to determine whether the **system specification itself can serve as the foundation for generation**.

---

## 3. Scope

This experiment will generate a small synthetic dataset for a single entity.

The experiment will intentionally remain simple.

### Included

- Entity definition
- Field definition
- Basic data types
- Basic semantic types
- Field-level generation
- Configurable record volume
- Deterministic generation where practical
- Generation output

### Excluded

- Real production data
- Machine Learning
- Large Language Models
- Statistical inference
- Cross-entity relationships
- Complex business rules
- Correlation between fields
- Domain-specific SAP, PLM, MES or ERP logic
- Advanced validation

These capabilities will be explored in later experiments.

---

## 4. Initial Entity

The experiment will use a generic `CUSTOMER` entity.

Example fields:

| Field | Type | Semantic |
|---|---|---|
| CUSTOMER_ID | string | identifier |
| COUNTRY | string | country |
| CUSTOMER_TYPE | string | categorical |
| CREATED_DATE | date | date |

The entity is intentionally domain-neutral.

---

## 5. Expected Output

The experiment should produce a dataset similar to:

```text
CUSTOMER_ID  COUNTRY  CUSTOMER_TYPE  CREATED_DATE
-----------  -------  -------------  ------------
C000001      US       BUSINESS       2026-01-14
C000002      DE       BUSINESS       2026-02-03
C000003      IN       INDIVIDUAL     2026-02-18
...