# Experiment 019: Generation Evidence / Provenance

**Status:** Planned  
**Experiment Type:** Evidence / Traceability / Validation / Architecture  
**FORGE Area:** Generation Evidence / Provenance  
**Objective:** Determine whether FORGE can capture sufficient evidence about how each generated value was produced to make the synthetic dataset explainable, traceable, and reproducible.

---

## 1. Research Question

Can FORGE capture generation evidence for synthetic data in a structured way that explains:

- Which specification produced a value
- Which generation strategy was used
- Which seed or random context was used
- Which constraints or dependencies influenced the value
- Whether the value was generated directly or derived from another value
- Which parent or related record influenced the value
- Which scenario was active
- Which validation rules were subsequently applied

The key question is:

> Can FORGE provide a useful provenance trail for generated data without requiring the generator to expose its internal implementation details?

The experiment will focus on the minimum evidence required to answer:

> **"Why does this generated value have this value?"**

---

## 2. Hypothesis

A structured generation-evidence model should allow FORGE to explain the origin of generated values without storing the entire internal execution state of the generator.

The hypothesis is that generation provenance can be represented through a combination of:

```text
Specification
     │
     ▼
Generation Strategy
     │
     ▼
Generation Context
     │
     ├── Seed
     ├── Scenario
     ├── Dependencies
     ├── Constraints
     └── Parent Reference
     │
     ▼
Generated Value
     │
     ▼
Evidence
````

For example, an evidence record could explain:

```text
ORDER_AMOUNT
    │
    ├── Strategy: parent_dependent
    ├── Parent: CUSTOMER.CUS0000042
    ├── Parent field: CUSTOMER_TYPE
    ├── Parent value: PREMIUM
    ├── Range: 5000 - 15000
    ├── Seed: 42
    └── Scenario: NORMAL
```

The evidence should explain the generation decision without requiring the generator to persist every intermediate random-number operation.

The experiment intentionally does not assume that complete execution replay is required for useful provenance.

It also does not assume that every generated value requires an independent evidence record.

The experiment should determine an appropriate evidence granularity.

The hypothesis should be rejected if the proposed evidence model cannot explain important generation decisions or if provenance becomes so large that it is impractical to retain.

---

## 3. Scope

This experiment will generate a small dataset using multiple generation strategies and capture provenance evidence for selected generated values.

### Included

* Dataset-level provenance
* Entity-level provenance
* Field-level provenance
* Generation strategy
* Generation seed
* Generation scenario
* Parent dependency
* Constraint influence
* Relationship influence
* Source specification reference
* Generated value evidence
* Evidence identifiers
* Provenance serialization
* Evidence lookup for individual generated values
* Reproducibility reference

### Excluded

* Full execution tracing
* Debug-level generator logs
* Storage of every random-number operation
* Cryptographic audit trails
* Distributed execution tracing
* Production-scale provenance storage
* Data lineage outside FORGE
* External source-system lineage

These capabilities may be explored later if required.

---

## 4. Initial Dataset / Entity

The experiment will use a small CUSTOMER / ORDER model so that different provenance patterns can be demonstrated.

### Entity

`CUSTOMER`

### Fields

| Field         | Type        | Semantic / Behavior             |
| ------------- | ----------- | ------------------------------- |
| CUSTOMER_ID   | identifier  | Primary identity                |
| CUSTOMER_TYPE | categorical | STANDARD or PREMIUM             |
| COUNTRY       | categorical | Weighted categorical generation |
| EMAIL         | string      | Optional population             |

### Entity

`ORDER`

### Fields

| Field       | Type       | Semantic / Behavior                         |
| ----------- | ---------- | ------------------------------------------- |
| ORDER_ID    | identifier | Primary identity                            |
| CUSTOMER_ID | identifier | Parent reference                            |
| AMOUNT      | number     | Parent-dependent generation                 |
| DISCOUNT    | number     | Constraint / scenario influenced generation |

The model is intentionally small.

The purpose of this experiment is provenance rather than generation complexity.

---

## 5. Experiment Configuration

The specification will explicitly declare generation strategies and dependencies.

Example:

```json
{
  "generation": {
    "seed": 42,
    "scenario": "NORMAL"
  }
}
```

A field may declare a direct generation strategy:

```json
{
  "field": "COUNTRY",
  "strategy": "weighted",
  "parameters": {
    "US": 0.50,
    "IN": 0.30,
    "DE": 0.15,
    "FR": 0.05
  }
}
```

A dependent field may declare:

```json
{
  "field": "AMOUNT",
  "strategy": "parent_dependent",
  "depends_on": {
    "entity": "CUSTOMER",
    "field": "CUSTOMER_TYPE"
  }
}
```

The provenance model should reference these declarations rather than duplicating the entire specification for every generated value.

---

## 6. Evidence Model

The experiment will investigate a hierarchical evidence model.

Conceptually:

```text
Generation Run
    │
    ├── Specification ID
    ├── Specification Version
    ├── Seed
    ├── Scenario
    └── Run ID
          │
          ├── Entity
          │     │
          │     └── Field
          │            │
          │            └── Value Evidence
          │
          └── Validation Evidence
```

A field-level evidence record may look like:

```json
{
  "evidence_id": "EV-000001",
  "run_id": "RUN-0001",
  "entity": "ORDER",
  "field": "AMOUNT",
  "record_id": "ORD0000001",
  "strategy": "parent_dependent",
  "seed": 42,
  "scenario": "NORMAL",
  "parent": {
    "entity": "CUSTOMER",
    "record_id": "CUS0000042",
    "field": "CUSTOMER_TYPE",
    "value": "PREMIUM"
  },
  "generation_parameters": {
    "min": 5000,
    "max": 15000
  },
  "generated_value": 8241.52
}
```

The exact structure will be refined during implementation.

---

## 7. Evidence Levels

The experiment will evaluate three levels of provenance.

### 7.1 Run-Level Evidence

Captures information common to the entire generation run.

Example:

```text
Run ID
Specification ID
Specification version
Seed
Scenario
Generation timestamp
Generator version
```

---

### 7.2 Field-Level Evidence

Captures how a field was generated.

Example:

```text
Entity: CUSTOMER
Field: COUNTRY
Strategy: weighted
Distribution:
    US = 50%
    IN = 30%
    DE = 15%
    FR = 5%
```

---

### 7.3 Value-Level Evidence

Captures why an individual value was produced.

Example:

```text
ORDER_AMOUNT = 8241.52

Generated because:

    Strategy:
        parent_dependent

    Parent:
        CUSTOMER.CUS0000042

    Parent field:
        CUSTOMER_TYPE

    Parent value:
        PREMIUM

    Generation range:
        5000 - 15000

    Seed:
        42
```

The experiment will determine whether all three levels are required or whether run-level and field-level evidence can sufficiently explain most generation behavior.

---