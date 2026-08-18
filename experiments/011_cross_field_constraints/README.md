# Experiment 011: Cross-Field Constraints

**Status:** Planned  
**Experiment Type:** Rule / Structural  
**FORGE Area:** Specification / Generation / Validation  
**Objective:** Determine whether cross-field constraints require dependency-aware generation rather than independent field generation.

---

## 1. Research Question

Can synthetic data satisfy constraints that depend on the relationship between multiple fields?

For example:

```text
START_DATE <= END_DATE
````

or:

```text
MIN_AMOUNT <= MAX_AMOUNT
```

If each field is generated independently, these relationships may be violated.

The experiment will determine whether cross-field constraints should influence the order and strategy of generation.

---

## 2. Hypothesis

Independent field generation will produce structurally valid individual fields but will not reliably satisfy relationships between fields.

Constraint-aware generation should significantly improve cross-field validity by generating dependent fields with awareness of previously generated values.

The hypothesis will be considered supported if:

* Independent generation produces measurable constraint violations.
* Individual field constraints remain valid even when cross-field constraints fail.
* Constraint-aware generation can produce valid field combinations.
* The constraint can be declared independently from the field generators.
* Validation can identify cross-field violations without embedding the constraint inside individual field generators.
* Generation can use the constraint to determine an appropriate generation dependency.

The hypothesis will be rejected if independent generation consistently satisfies the cross-field constraints without requiring coordination, or if cross-field constraints cannot be represented independently from field generation.

---

## 3. Scope

This experiment will generate a generic entity containing pairs of fields whose values must satisfy explicit relationships.

The experiment will compare:

```text
Approach A
-----------
Independent field generation

Approach B
-----------
Constraint-aware generation
```

### Included

* Multiple fields
* Field-level constraints
* Cross-field constraints
* Independent generation
* Constraint-aware generation
* Generation dependency
* Cross-field validation
* Constraint violation detection
* Deterministic generation
* Generation output

### Excluded

* Real production data
* Machine Learning
* Deep Learning
* Large Language Models
* Cross-entity relationships
* Statistical inference
* Correlation modeling
* Complex rule chains
* Conditional population
* Temporal lifecycle modeling
* Scenario generation
* Constraint conflict resolution

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a generic `ORDER` entity.

The entity will contain two pairs of fields with explicit cross-field relationships.

### Entity

`ORDER`

### Fields

| Field        | Type       | Semantic / Behavior                           |
| ------------ | ---------- | --------------------------------------------- |
| ORDER_ID     | identifier | Unique order identifier                       |
| START_DATE   | date       | Order start date                              |
| END_DATE     | date       | Must be greater than or equal to START_DATE   |
| MIN_AMOUNT   | number     | Lower monetary bound                          |
| MAX_AMOUNT   | number     | Must be greater than or equal to MIN_AMOUNT   |
| ORDER_AMOUNT | number     | Order amount within MIN_AMOUNT and MAX_AMOUNT |

The primary cross-field constraints are:

```text
START_DATE <= END_DATE
```

and:

```text
MIN_AMOUNT <= MAX_AMOUNT
```

A secondary constraint will also be tested:

```text
MIN_AMOUNT <= ORDER_AMOUNT <= MAX_AMOUNT
```

---

## 5. Experiment Configuration

Cross-field constraints will be declared separately from the individual field definitions.

Example:

```json
{
  "constraints": [
    {
      "type": "comparison",
      "left": "START_DATE",
      "operator": "less_than_or_equal",
      "right": "END_DATE"
    },
    {
      "type": "comparison",
      "left": "MIN_AMOUNT",
      "operator": "less_than_or_equal",
      "right": "MAX_AMOUNT"
    },
    {
      "type": "range",
      "field": "ORDER_AMOUNT",
      "minimum_field": "MIN_AMOUNT",
      "maximum_field": "MAX_AMOUNT"
    }
  ]
}
```

The important architectural separation is:

```text
Field Definition
       │
       ├── Type
       ├── Domain
       └── Generation

Cross-Field Constraint
       │
       ├── Fields involved
       ├── Operator
       └── Relationship
```

The field generator should not need to know that another field depends on it.

---

## 6. Approach A: Independent Generation

In the first approach, every field will be generated independently.

Conceptually:

```text
Generate START_DATE
Generate END_DATE

Generate MIN_AMOUNT
Generate MAX_AMOUNT

Generate ORDER_AMOUNT
```

No field will be aware of another field during generation.

The generated dataset will then be validated against the declared constraints.

This approach is intentionally expected to produce failures.

For example:

```text
START_DATE = 2026-08-20
END_DATE   = 2026-08-12
```

is individually valid but violates:

```text
START_DATE <= END_DATE
```

Similarly:

```text
MIN_AMOUNT = 9000
MAX_AMOUNT = 2000
```

is individually valid but violates:

```text
MIN_AMOUNT <= MAX_AMOUNT
```

---

## 7. Approach B: Constraint-Aware Generation

In the second approach, generation will use the declared constraints to coordinate dependent fields.

For example:

```text
Generate START_DATE
        ↓
Generate END_DATE
        │
        └── END_DATE >= START_DATE
```

and:

```text
Generate MIN_AMOUNT
        ↓
Generate MAX_AMOUNT
        │
        └── MAX_AMOUNT >= MIN_AMOUNT
```

For the order amount:

```text
Generate MIN_AMOUNT
        ↓
Generate MAX_AMOUNT
        ↓
Generate ORDER_AMOUNT
        │
        └── MIN_AMOUNT <= ORDER_AMOUNT <= MAX_AMOUNT
```

The experiment will determine whether this dependency-aware approach can eliminate violations without moving constraint logic into individual field generators.

---