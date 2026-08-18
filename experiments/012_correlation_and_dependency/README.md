# Experiment 012: Correlation and Dependency

**Status:** Planned  
**Experiment Type:** Statistical / Dependency  
**FORGE Area:** Specification / Generation  
**Objective:** Determine whether meaningful relationships between fields require explicit dependency-aware generation rather than independent field generation.

---

## 1. Research Question

Can synthetic data preserve meaningful relationships between fields when those relationships are explicitly defined in the generation specification?

For example:

```text
CUSTOMER_TYPE
      │
      ├──> CUSTOMER_LIMIT
      │
      └──> ORDER_AMOUNT
````

If these fields are generated independently, the resulting dataset may satisfy all individual field constraints while still producing unrealistic combinations.

The experiment will determine whether explicit dependency information can produce measurable and predictable relationships between generated fields.

---

## 2. Hypothesis

Independent generation of related fields will produce little or no meaningful relationship between them, even when each individual field is structurally valid.

Dependency-aware generation should produce a measurable relationship that reflects the declared dependency.

The hypothesis will be considered supported if:

* Independent generation produces structurally valid fields but weak or absent relationships.
* Dependency-aware generation produces a measurable relationship between dependent fields.
* Categorical dependencies produce distinguishable distributions across categories.
* Numeric dependencies produce measurable statistical association.
* The dependency can be declared separately from the individual field definitions.
* The resulting relationship can be measured independently from generation.

The hypothesis will be rejected if independent generation naturally produces equivalent relationships, or if explicit dependency information does not materially change the observed relationship.

---

## 3. Scope

This experiment will generate a generic customer dataset containing categorical and numeric fields with an intentionally defined dependency.

The experiment will compare:

```text
Approach A
-----------
Independent generation

Approach B
-----------
Dependency-aware generation
```

The experiment will focus on whether dependency information changes the statistical relationship between fields.

### Included

* Categorical fields
* Numeric fields
* Independent generation
* Dependency-aware generation
* Categorical-to-numeric dependency
* Numeric-to-numeric dependency
* Correlation measurement
* Group-level statistical comparison
* Deterministic generation
* Generation output

### Excluded

* Real production data
* Machine Learning
* Deep Learning
* Large Language Models
* Cross-entity relationships
* Foreign keys
* Composite identities
* Hard cross-field constraints
* Conditional population
* Complex dependency graphs
* Statistical inference from real data
* Causal inference
* Advanced multivariate distributions

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a generic `CUSTOMER` entity.

The entity will contain a customer classification and numeric attributes whose behavior is expected to depend on that classification.

### Entity

`CUSTOMER`

### Fields

| Field          | Type        | Semantic / Behavior                             |
| -------------- | ----------- | ----------------------------------------------- |
| CUSTOMER_ID    | identifier  | Unique customer identifier                      |
| CUSTOMER_TYPE  | categorical | Customer classification                         |
| CUSTOMER_LIMIT | number      | Financial limit associated with customer type   |
| ORDER_AMOUNT   | number      | Transaction amount influenced by customer limit |

The experiment will use two customer types:

```text
STANDARD
PREMIUM
```

The expected behavior is:

```text
STANDARD
    ↓
lower CUSTOMER_LIMIT
    ↓
lower typical ORDER_AMOUNT

PREMIUM
    ↓
higher CUSTOMER_LIMIT
    ↓
higher typical ORDER_AMOUNT
```

The exact numeric ranges will be defined in `specification.json`.

---

## 5. Experiment Configuration

The dependency will be declared separately from the field definitions.

Example:

```json
{
  "dependencies": [
    {
      "type": "categorical_to_numeric",
      "source": "CUSTOMER_TYPE",
      "target": "CUSTOMER_LIMIT"
    },
    {
      "type": "numeric_to_numeric",
      "source": "CUSTOMER_LIMIT",
      "target": "ORDER_AMOUNT"
    }
  ]
}
```

The important distinction is:

```text
Field Definition
       │
       ├── Type
       ├── Domain
       └── Generation

Dependency Definition
       │
       ├── Source
       ├── Target
       └── Dependency behavior
```

The individual field generators should not need to contain knowledge of the dependency.

---

## 6. Approach A: Independent Generation

In the first approach, all fields will be generated independently.

Conceptually:

```text
Generate CUSTOMER_TYPE
        │
        └── no influence

Generate CUSTOMER_LIMIT
        │
        └── no influence

Generate ORDER_AMOUNT
        │
        └── no influence
```

This should produce valid individual fields but should not intentionally produce a meaningful relationship between them.

For example:

```text
CUSTOMER_TYPE = STANDARD
CUSTOMER_LIMIT = 900000
ORDER_AMOUNT = 850000
```

could occur even though such a combination may not represent the intended synthetic population.

The experiment will measure the resulting relationships rather than declaring them invalid.

---

## 7. Approach B: Dependency-Aware Generation

In the second approach, generation will use the declared dependencies.

Conceptually:

```text
CUSTOMER_TYPE
      │
      ▼
CUSTOMER_LIMIT
      │
      ▼
ORDER_AMOUNT
```

For example:

```text
CUSTOMER_TYPE = STANDARD
        ↓
CUSTOMER_LIMIT generated from
STANDARD-specific behavior
        ↓
ORDER_AMOUNT generated relative
to CUSTOMER_LIMIT
```

For:

```text
CUSTOMER_TYPE = PREMIUM
```

the generated values should reflect a different expected range or behavior.

The objective is not merely to enforce a hard constraint.

The objective is to create a **statistical relationship** between the fields.

---