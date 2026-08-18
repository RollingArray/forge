# Experiment 010: Composite Identity

**Status:** Planned  
**Experiment Type:** Structural / Identity  
**FORGE Area:** Specification / Generation  
**Objective:** Determine whether composite keys should be modeled and generated as a single identity construct rather than as independent fields.

---

## 1. Research Question

Can a composite identity be generated reliably when its constituent fields are treated as a coordinated identity rather than as independent fields?

For example:

```text
CUSTOMER_ACCOUNT
    ├── COMPANY_CODE
    ├── CUSTOMER_NUMBER
    └── ACCOUNT_TYPE
````

may together form:

```text
PRIMARY KEY
(
    COMPANY_CODE,
    CUSTOMER_NUMBER,
    ACCOUNT_TYPE
)
```

The experiment will determine whether these fields can safely be generated independently while preserving composite uniqueness, or whether the composite key itself needs to become a first-class generation concept.

---

## 2. Hypothesis

A composite key should be represented as a coordinated identity construct.

Although each component of a composite key has its own:

* data type
* format
* domain
* constraints

the combination of those fields represents a single identity.

The hypothesis will be considered supported if:

* Individual key components can retain their own field-level definitions.
* The composite key can be declared explicitly in metadata.
* Generated records remain unique based on the complete composite key.
* Individual components may legitimately repeat across records.
* The generator can coordinate the components when uniqueness depends on their combination.
* Composite identity can be validated independently from individual field validation.

The hypothesis will be rejected if treating composite key components as independent fields produces equivalent behavior without requiring any additional identity-level concept.

---

## 3. Scope

This experiment will generate a generic entity with a three-field composite identity.

The experiment will intentionally compare two approaches:

```text
Approach A
-----------
Generate each key field independently.

Approach B
-----------
Generate the composite identity as a coordinated unit.
```

The resulting datasets will be compared for uniqueness and identity behavior.

### Included

* Composite key definition
* Multiple key components
* Field-level constraints within a composite key
* Independent component generation
* Coordinated composite identity generation
* Composite uniqueness validation
* Duplicate detection
* Deterministic generation
* Generation output

### Excluded

* Real production data
* Machine Learning
* Deep Learning
* Large Language Models
* Foreign-key relationships
* Cross-entity composite relationships
* Complex business rules
* Statistical distributions
* Correlation between non-key attributes
* Temporal identity
* Scenario generation

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a generic `CUSTOMER_ACCOUNT` entity.

The entity will use three fields as a composite identity.

### Entity

`CUSTOMER_ACCOUNT`

### Fields

| Field           | Type        | Semantic / Behavior                |
| --------------- | ----------- | ---------------------------------- |
| COMPANY_CODE    | categorical | Company identifier                 |
| CUSTOMER_NUMBER | identifier  | Customer identifier within company |
| ACCOUNT_TYPE    | categorical | Account classification             |
| CUSTOMER_NAME   | string      | Non-key descriptive field          |

The composite identity will be:

```text
(
    COMPANY_CODE,
    CUSTOMER_NUMBER,
    ACCOUNT_TYPE
)
```

For example:

```text
COMPANY_CODE | CUSTOMER_NUMBER | ACCOUNT_TYPE
-------------|-----------------|-------------
1000         | 000001          | STANDARD
1000         | 000001          | PREMIUM
1000         | 000002          | STANDARD
2000         | 000001          | STANDARD
```

Notice that:

```text
CUSTOMER_NUMBER = 000001
```

can appear multiple times.

That is valid because identity is determined by the combination of all three fields.

---

## 5. Experiment Configuration

The composite identity will be explicitly declared in the specification.

Example:

```json
{
  "entities": {
    "CUSTOMER_ACCOUNT": {
      "identity": {
        "type": "composite",
        "fields": [
          "COMPANY_CODE",
          "CUSTOMER_NUMBER",
          "ACCOUNT_TYPE"
        ]
      }
    }
  }
}
```

The individual fields will continue to contain their own generation definitions.

Example:

```json
{
  "COMPANY_CODE": {
    "type": "categorical",
    "values": [
      "1000",
      "2000",
      "3000"
    ]
  },

  "CUSTOMER_NUMBER": {
    "type": "identifier",
    "length": 6
  },

  "ACCOUNT_TYPE": {
    "type": "categorical",
    "values": [
      "STANDARD",
      "PREMIUM"
    ]
  }
}
```

The experiment will therefore test the relationship between:

```text
Entity Identity
       │
       └── Composite Identity
               │
               ├── COMPANY_CODE
               ├── CUSTOMER_NUMBER
               └── ACCOUNT_TYPE
```

and:

```text
Field Generation
       │
       ├── COMPANY_CODE generator
       ├── CUSTOMER_NUMBER generator
       └── ACCOUNT_TYPE generator
```

---

## 6. Approach A: Independent Generation

In the first approach, each field will be generated independently.

Conceptually:

```text
Generate COMPANY_CODE
        ↓
Generate CUSTOMER_NUMBER
        ↓
Generate ACCOUNT_TYPE
        ↓
Create composite key
```

The generator will then check whether the resulting combination has already been generated.

Example:

```text
1000 | 000001 | STANDARD
1000 | 000001 | PREMIUM
1000 | 000002 | STANDARD
```

The individual fields are generated independently.

The experiment will measure whether duplicate composite identities occur as record volume increases.

---

## 7. Approach B: Coordinated Composite Generation

In the second approach, the composite identity will be treated as a generation unit.

Conceptually:

```text
Composite Identity Generator
            ↓
     ┌──────┼──────┐
     ↓      ↓      ↓
 COMPANY  CUSTOMER ACCOUNT
  CODE     NUMBER   TYPE
```

The generator will select or construct a unique combination and then assign the individual components.

This approach explicitly treats:

```text
(
    COMPANY_CODE,
    CUSTOMER_NUMBER,
    ACCOUNT_TYPE
)
```

as one identity.

---