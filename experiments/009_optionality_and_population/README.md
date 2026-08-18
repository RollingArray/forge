# Experiment 009: Optionality and Population

**Status:** Planned  
**Experiment Type:** Structural / Rule  
**FORGE Area:** Specification / Generation  
**Objective:** Determine how FORGE should represent optional fields, population rates, and conditional population behavior.

---

## 1. Research Question

How should FORGE distinguish between:

1. A field that is optional,
2. A field that is populated probabilistically, and
3. A field whose population depends on another field or condition?

For example:

```text
PHONE
    population_rate = 0.80
````

is fundamentally different from:

```text
COUNTRY = US
    ↓
TAX_ID populated

COUNTRY != US
    ↓
TAX_ID null
```

The experiment will determine whether these behaviors should be represented as field-level metadata, generation strategies, or rules.

---

## 2. Hypothesis

Field optionality and population behavior should be represented separately.

A field's optionality should describe whether the field is allowed to be null.

Population behavior should describe how often or under what conditions the field receives a value.

The experiment will test the following model:

```text
Field
 │
 ├── nullable
 │
 └── population
       │
       ├── unconditional
       │       └── population_rate
       │
       └── conditional
               └── condition / rule
```

The hypothesis will be considered supported if:

* A nullable field can be generated without requiring a population rule.
* A population rate can control unconditional population.
* A non-nullable field cannot become null because of a population rate.
* Conditional population can depend on another field.
* The same field-generation mechanism can be used whether a field is always populated, probabilistically populated, or conditionally populated.
* Population behavior can be expressed declaratively in the specification.

The hypothesis will be rejected if optionality and population behavior cannot be cleanly separated or if conditional population requires embedding business logic directly inside field generators.

---

## 3. Scope

This experiment will generate a `CUSTOMER` dataset containing fields with different optionality and population behaviors.

The experiment will progress from simple unconditional population to conditional population.

### Included

* Non-nullable fields
* Nullable fields
* Always-populated fields
* Population rates
* Zero population rate
* Full population rate
* Conditional population
* Field-dependent population
* Population validation
* Declarative population configuration

### Excluded

* Real production data
* Machine Learning
* Deep Learning
* Large Language Models
* Complex business rules
* Cross-entity relationships
* Statistical inference
* Cross-field correlation
* Temporal dependencies
* Scenario generation
* Advanced rule evaluation

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a generic `CUSTOMER` entity.

The fields will intentionally represent different population behaviors.

### Entity

`CUSTOMER`

### Fields

| Field       | Type        | Semantic / Behavior               |
| ----------- | ----------- | --------------------------------- |
| CUSTOMER_ID | identifier  | Always populated                  |
| COUNTRY     | categorical | Always populated                  |
| EMAIL       | string      | 80% population rate               |
| PHONE       | string      | 50% population rate               |
| TAX_ID      | string      | Populated only for US customers   |
| ADDRESS     | string      | Nullable and optionally populated |

The experiment will use the following population concepts:

```text
CUSTOMER_ID
    → always populated

EMAIL
    → population_rate = 0.80

PHONE
    → population_rate = 0.50

TAX_ID
    → COUNTRY = US
        → populated

    → COUNTRY != US
        → null

ADDRESS
    → nullable
    → population_rate = 0.60
```

---

## 5. Experiment Configuration

The experiment will explicitly separate field nullability from population behavior.

Example:

```json
{
  "fields": {
    "EMAIL": {
      "type": "string",
      "nullable": true,
      "population": {
        "type": "rate",
        "rate": 0.80
      }
    },

    "TAX_ID": {
      "type": "string",
      "nullable": true,
      "population": {
        "type": "conditional",
        "condition": {
          "field": "COUNTRY",
          "operator": "equals",
          "value": "US"
        }
      }
    }
  }
}
```

The architectural distinction being tested is:

```text
nullable
    =
whether NULL is permitted

population
    =
when a value should be generated
```

---

## 6. Population Behaviors

The experiment will evaluate several population behaviors.

### 6.1 Always Populated

A field with:

```text
nullable = false
```

must always contain a value.

Example:

```text
CUSTOMER_ID
```

Expected:

```text
100% populated
0% null
```

---

### 6.2 Always Populated Nullable Field

A field may technically permit nulls but can be configured for full population.

Example:

```text
population_rate = 1.0
```

Expected:

```text
100% populated
```

This allows the experiment to determine whether nullability and population should remain independent.

---

### 6.3 Rate-Based Population

A nullable field can specify a population rate.

Example:

```text
EMAIL
    population_rate = 0.80
```

Expected behavior for a sufficiently large dataset:

```text
approximately 80% populated
approximately 20% null
```

The experiment will observe the actual population rate but will not establish formal statistical acceptance criteria.

Formal statistical validation is reserved for Experiment 016.

---

### 6.4 Zero Population

The experiment will also test:

```text
population_rate = 0.0
```

Expected:

```text
0% populated
100% null
```

This is important because boundary values should be explicitly tested.

---

### 6.5 Conditional Population

A field can be populated based on another field.

Example:

```text
COUNTRY = US
    ↓
TAX_ID populated

COUNTRY != US
    ↓
TAX_ID null
```

The population decision therefore depends on the generated value of another field.

This introduces a dependency between fields without introducing a general-purpose business rule engine.

---