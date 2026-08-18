# Experiment 014: Parent-Dependent Generation

**Status:** Planned  
**Experiment Type:** Relationship / Statistical / Dependency  
**FORGE Area:** Relationship-Aware Generation  
**Objective:** Determine whether child-field generation can be controlled by attributes of the related parent entity while maintaining referential integrity and the declared parent-dependent distributions.

---

## 1. Research Question

Can FORGE generate child records whose field distributions depend on attributes of their related parent records?

For example:

```text
CUSTOMER
├── CUSTOMER_ID
└── CUSTOMER_TYPE
        │
        │ 1:N
        ▼
ORDER
├── ORDER_ID
├── CUSTOMER_ID
└── AMOUNT
````

where:

```text
CUSTOMER_TYPE = STANDARD
    → ORDER.AMOUNT follows distribution A

CUSTOMER_TYPE = PREMIUM
    → ORDER.AMOUNT follows distribution B
```

The experiment will determine whether this dependency can be declared as metadata and interpreted generically by the generation engine.

---

## 2. Hypothesis

A child field can be generated according to the attributes of its related parent entity when the dependency is explicitly declared in the specification.

The generator should be able to:

* Generate parent records first.
* Generate child records while resolving the appropriate parent.
* Read the relevant parent attribute.
* Select the corresponding child generation behavior.
* Preserve the declared child-field constraints.
* Preserve referential integrity.
* Produce measurably different child distributions for different parent groups.

The hypothesis should be considered supported if parent groups with different declared generation behavior produce distinguishable child-field distributions.

The hypothesis will be rejected if parent-dependent generation requires hard-coded entity-specific logic or if the generated child distribution does not reflect the declared parent dependency.

---

## 3. Scope

This experiment will extend the relationship and dependency concepts established in Experiments 012 and 013.

The experiment will compare:

```text
Approach A
Independent child generation

versus

Approach B
Parent-dependent child generation
```

### Included

* Parent entity attributes
* Parent-child relationships
* `1:N` relationships
* Child-field generation dependent on parent attributes
* Group-specific numeric distributions
* Parent-aware generation
* Referential integrity
* Distribution comparison between parent groups
* Field-level validation
* Relationship validation
* Deterministic generation

### Excluded

* Multi-level parent dependency chains
* Multiple parent attributes controlling the same child field
* Conditional relationship creation
* Many-to-many parent-dependent generation
* Composite keys
* Temporal dependencies
* Scenario generation
* Real production data
* Machine Learning
* Large Language Models

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a domain-neutral customer and order model.

### Entity

`CUSTOMER`

### Fields

| Field         | Type        | Semantic / Behavior                           |
| ------------- | ----------- | --------------------------------------------- |
| CUSTOMER_ID   | identifier  | Unique customer identity                      |
| CUSTOMER_TYPE | categorical | Parent attribute controlling child generation |
| COUNTRY       | categorical | Independent customer attribute                |

### Entity

`ORDER`

### Fields

| Field       | Type       | Semantic / Behavior                                     |
| ----------- | ---------- | ------------------------------------------------------- |
| ORDER_ID    | identifier | Unique order identity                                   |
| CUSTOMER_ID | identifier | Reference to CUSTOMER                                   |
| AMOUNT      | number     | Child field whose distribution depends on CUSTOMER_TYPE |

The relationship is:

```text
CUSTOMER
    1
    │
    │
    N
ORDER
```

---

## 5. Parent-Dependent Behavior

The experiment will introduce a dependency such as:

```text
CUSTOMER.CUSTOMER_TYPE
        │
        ▼
ORDER.AMOUNT
```

For example:

```text
STANDARD
    → ORDER.AMOUNT: 100 - 2,000

PREMIUM
    → ORDER.AMOUNT: 2,000 - 10,000
```

The exact ranges will be declared in `specification.json`.

The important point is that the ranges are not properties of the child field alone.

Instead:

```text
ORDER.AMOUNT
```

has different generation behavior depending on:

```text
CUSTOMER.CUSTOMER_TYPE
```

---

## 6. Experiment Configuration

The parent-dependent behavior will be represented separately from the field definition.

Example:

```json
{
  "dependencies": [
    {
      "id": "D001",
      "type": "parent_dependent",
      "parent_entity": "CUSTOMER",
      "parent_field": "CUSTOMER_TYPE",
      "child_entity": "ORDER",
      "child_field": "AMOUNT",
      "behavior": {
        "STANDARD": {
          "distribution": {
            "type": "uniform",
            "min": 100,
            "max": 2000
          }
        },
        "PREMIUM": {
          "distribution": {
            "type": "uniform",
            "min": 2000,
            "max": 10000
          }
        }
      }
    }
  ]
}
```

This keeps the dependency separate from both:

```text
CUSTOMER
```

and:

```text
ORDER.AMOUNT
```

---