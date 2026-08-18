# Experiment 015: Scenario Generation

**Status:** Planned  
**Experiment Type:** Generation / Configuration / Validation  
**FORGE Area:** Scenario-Aware Generation  
**Objective:** Determine whether a base data specification can be combined with a declarative scenario to generate datasets with coherent, scenario-specific characteristics.

---

## 1. Research Question

Can FORGE apply a declared scenario as an overlay on a base specification so that multiple generation behaviors change coherently without modifying the underlying entity and field definitions?

For example:

```text
Base Specification
        │
        ▼
Scenario: HIGH_VALUE
        │
        ├── CUSTOMER_TYPE distribution
        ├── ORDER amount distribution
        ├── relationship allocation
        └── population behavior
                │
                ▼
        Scenario-specific dataset
````

The experiment will determine whether a scenario should be modeled as a generation configuration layered over the base specification rather than embedded directly into individual field definitions.

---

## 2. Hypothesis

A scenario can be represented as a declarative configuration that overrides or modifies selected generation behaviors while preserving the base specification.

The generator should be able to:

* Generate a baseline dataset from the base specification.
* Apply a declared scenario without changing the base entity definitions.
* Override selected generation behaviors.
* Leave unspecified behaviors unchanged.
* Produce materially different datasets for different scenarios.
* Preserve field-level constraints.
* Preserve relationships and dependencies.
* Maintain deterministic generation when the same scenario and seed are used.

The hypothesis should be considered supported if multiple scenarios can produce distinct, internally consistent datasets from the same base specification.

The hypothesis will be rejected if scenario behavior requires modifying the base specification or introducing scenario-specific generation logic into individual field generators.

---

## 3. Scope

This experiment will test scenarios as configuration overlays applied to a common base dataset specification.

The experiment will compare:

```text
Base Specification
        ↓
Normal Generation
```

against:

```text
Base Specification
        +
Scenario Configuration
        ↓
Scenario Generation
```

### Included

* Base specification
* Scenario definitions
* Scenario-level overrides
* Field generation overrides
* Population overrides
* Distribution overrides
* Parent-dependent generation overrides
* Scenario-specific generation seeds
* Deterministic scenario generation
* Scenario comparison
* Structural validation
* Relationship validation

### Excluded

* Automatic scenario discovery
* Machine learning-based scenario generation
* Natural-language scenario interpretation
* Scenario inheritance
* Nested scenarios
* Scenario combinations
* Temporal scenario sequencing
* Production-scale performance testing

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a domain-neutral customer and order model.

The same base specification will be used for all scenarios.

### Entity

`CUSTOMER`

### Fields

| Field         | Type        | Semantic / Behavior          |
| ------------- | ----------- | ---------------------------- |
| CUSTOMER_ID   | identifier  | Unique customer identity     |
| CUSTOMER_TYPE | categorical | Customer classification      |
| COUNTRY       | categorical | Customer geographic domain   |
| EMAIL         | string      | Optional contact information |

### Entity

`ORDER`

### Fields

| Field       | Type       | Semantic / Behavior   |
| ----------- | ---------- | --------------------- |
| ORDER_ID    | identifier | Unique order identity |
| CUSTOMER_ID | identifier | Reference to CUSTOMER |
| AMOUNT      | number     | Order monetary value  |

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

## 5. Scenario Model

A scenario represents a desired generation condition.

The base specification defines the underlying data model:

```text
CUSTOMER
ORDER
relationships
fields
constraints
```

The scenario defines how generation should behave for a particular use case.

Conceptually:

```text
Base Specification
        │
        ├── entities
        ├── fields
        ├── relationships
        └── constraints
                │
                +
        Scenario Overlay
                │
                ▼
        Effective Specification
                │
                ▼
            Generator
```

The scenario should not redefine the entire dataset.

It should contain only the behavior that changes.

---

## 6. Initial Scenarios

The experiment will initially evaluate three scenarios.

### Scenario 1: NORMAL

Represents the default generation behavior.

```text
Scenario: NORMAL

No significant overrides.
```

This provides the baseline.

---

### Scenario 2: HIGH_VALUE

Represents a population with a greater proportion of premium customers and higher-value orders.

Example:

```text
CUSTOMER_TYPE

STANDARD → 40%
PREMIUM  → 60%
```

and:

```text
ORDER.AMOUNT

STANDARD → lower range
PREMIUM  → higher range
```

The exact values will be defined in `specification.json`.

The purpose is to determine whether multiple related generation behaviors can be changed through a single scenario.

---

### Scenario 3: MISSING_DATA

Represents a dataset with intentionally increased missingness.

Example:

```text
EMAIL population rate
    ↓
40%

Other fields
    ↓
unchanged
```

This tests whether a scenario can selectively modify population behavior without affecting unrelated generation behavior.

---

## 7. Experiment Configuration

The base specification and scenarios will be represented separately.

Example:

```json
{
  "base": {
    "entities": {
      "CUSTOMER": {},
      "ORDER": {}
    }
  },

  "scenarios": {
    "NORMAL": {
      "overrides": {}
    },

    "HIGH_VALUE": {
      "overrides": {
        "CUSTOMER.CUSTOMER_TYPE": {
          "distribution": {
            "type": "weighted"
          }
        }
      }
    },

    "MISSING_DATA": {
      "overrides": {
        "CUSTOMER.EMAIL": {
          "population_rate": 0.40
        }
      }
    }
  }
}
```

The exact configuration will be defined in the experiment specification.

The important principle is:

```text
Base specification
        +
Scenario override
        =
Effective generation behavior
```

---

## 8. Scenario Resolution

The experiment will test a simple scenario-resolution process.

```text
Load Base Specification
          │
          ▼
Load Scenario
          │
          ▼
Resolve Overrides
          │
          ▼
Effective Generation Configuration
          │
          ▼
Generate Dataset
```

If a scenario does not override a property, the base specification should remain effective.

For example:

```text
Base:
EMAIL population = 80%

HIGH_VALUE:
EMAIL population = not specified

Result:
EMAIL population = 80%
```

Whereas:

```text
Base:
EMAIL population = 80%

MISSING_DATA:
EMAIL population = 40%

Result:
EMAIL population = 40%
```

---