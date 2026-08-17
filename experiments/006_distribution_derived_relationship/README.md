# Experiment 006: Distribution-Derived Relationship Allocation

**Status:** Planned  
**Experiment Type:** Statistical / Relationship  
**FORGE Area:** Relationships / Statistical Generation  
**Objective:** Determine whether relationship allocation can be derived automatically from a declared statistical distribution without requiring explicit weights for individual parent records.

---

## 1. Research Question

Can synthetic child records be distributed across parent records using only a declared statistical distribution, without explicitly specifying the allocation or weight of each individual parent?

---

## 2. Hypothesis

A relationship distribution can be expressed as statistical intent rather than as explicit parent-level weights.

Instead of defining the allocation for every parent record, the generator should be able to derive parent-level allocation from a distribution model such as:

- Uniform distribution
- Power-law distribution

The generated relationship should maintain referential integrity while producing the expected statistical shape.

The hypothesis will be considered supported if:

- Parent-level weights can be derived automatically.
- The resulting child records maintain referential integrity.
- The declared `1:N` relationship is preserved.
- Different numbers of parent records can use the same distribution specification.
- The resulting relationship distribution follows the intended statistical behavior.

The experiment intentionally does not assume that real production data is available to determine the relationship distribution.

---

## 3. Scope

This experiment will build on the relationship generation capabilities established in Experiments 004 and 005 and investigate whether relationship distributions can be defined independently of individual parent records.

### Included

- Entity definition
- Field definition
- Field constraints
- Parent-child relationships
- `1:N` cardinality
- Uniform relationship allocation
- Power-law relationship allocation
- Automatic derivation of parent allocation
- Referential integrity validation
- Relationship distribution validation
- Configurable parent volume
- Configurable child volume
- Deterministic random seed
- Relationship statistics
- Transparent derived allocation

### Excluded

- Real production data
- Machine Learning
- Deep Learning
- Large Language Models
- Distribution inference from real data
- Explicit parent-level weights
- Cross-field correlation
- Conditional relationships
- Complex business rules
- Temporal relationships
- Many-to-many relationships
- Domain-specific SAP, PLM, MES or ERP logic
- Advanced statistical similarity metrics

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

This experiment will continue using the generic `CUSTOMER` and `ORDER` entities established in Experiments 004 and 005.

The dataset will remain domain-neutral.

### Entity

`CUSTOMER`

### Fields

| Field | Type | Semantic / Behavior |
|---|---|---|
| CUSTOMER_ID | identifier | Unique parent identifier |
| COUNTRY | categorical | Weighted categorical distribution |

### Entity

`ORDER`

### Fields

| Field | Type | Semantic / Behavior |
|---|---|---|
| ORDER_ID | identifier | Unique child identifier |
| AMOUNT | integer | Bounded numeric distribution |
| CUSTOMER_ID | reference | References `CUSTOMER.CUSTOMER_ID` |

---

## 5. Experiment Configuration

The experiment will describe the desired relationship distribution rather than explicitly defining the weight of every parent.

Example:

```json
{
  "relationship": {
    "parent_entity": "CUSTOMER",
    "parent_field": "CUSTOMER_ID",
    "child_entity": "ORDER",
    "child_field": "CUSTOMER_ID",
    "cardinality": "1:N",
    "distribution": {
      "type": "power_law",
      "parameters": {
        "alpha": 1.5
      }
    }
  }
}