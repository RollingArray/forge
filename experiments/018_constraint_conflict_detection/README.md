# Experiment 018: Constraint Conflict Detection

**Status:** Planned  
**Experiment Type:** Rule / Validation / Structural  
**FORGE Area:** Constraint Management  
**Objective:** Determine whether FORGE can detect contradictory or unsatisfiable constraints before attempting data generation.

---

## 1. Research Question

Can FORGE identify when declared constraints cannot be satisfied simultaneously?

The experiment specifically examines whether a constraint model can distinguish between:

- Valid constraints that can coexist
- Directly contradictory constraints
- Indirectly conflicting constraints
- Boundary conflicts
- Conditional conflicts
- Constraints that are individually valid but collectively unsatisfiable

The key question is:

> Can FORGE detect an impossible specification before generation rather than discovering the problem through generation failure?

---

## 2. Hypothesis

A sufficiently explicit constraint representation should allow FORGE to detect at least common classes of constraint conflicts before data generation begins.

For example:

```text
MIN_AMOUNT <= MAX_AMOUNT
MAX_AMOUNT <= 1000
MIN_AMOUNT >= 2000
````

Each constraint is individually valid.

Together they are impossible.

Similarly:

```text
CUSTOMER_TYPE = PREMIUM
CUSTOMER_TYPE = STANDARD
```

cannot both be satisfied for the same record.

The hypothesis is that FORGE should be able to identify such conflicts during specification validation.

The experiment should distinguish between:

```text
Constraint is valid
        ↓
Constraint set is compatible
        ↓
Constraint set is satisfiable
        ↓
Generation may proceed
```

and:

```text
Constraint is valid
        ↓
Constraint set is contradictory
        ↓
Generation must not proceed
```

The experiment is intentionally not assuming that FORGE can solve arbitrary logical satisfiability problems.

The initial scope is limited to conflicts that can be detected through explicit field relationships, ranges, categorical values, and simple conditional rules.

The hypothesis should be rejected if common constraint conflicts cannot be reliably identified before generation.

---

## 3. Scope

This experiment will define several constraint sets containing valid, conflicting, and indirectly conflicting rules and determine whether FORGE can classify them correctly before dataset generation.

### Included

* Direct numeric range conflicts
* Numeric boundary conflicts
* Cross-field inequality conflicts
* Categorical value conflicts
* Conditional constraint conflicts
* Compatible constraint sets
* Detection before generation
* Conflict identification
* Conflict evidence
* Constraint-level PASS / CONFLICT results
* Specification-level validation result

### Excluded

* General-purpose SAT solving
* General-purpose theorem proving
* Natural-language constraint interpretation
* Complex temporal logic
* Probabilistic constraint satisfaction
* Automatic constraint repair
* Automatic selection of conflicting constraints
* Optimization of conflicting specifications

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a small domain-neutral CUSTOMER / ORDER model.

The primary purpose of this experiment is to validate the **constraint specification**, rather than the generated dataset.

### Entity

`ORDER`

### Fields

| Field         | Type        | Semantic / Behavior                             |
| ------------- | ----------- | ----------------------------------------------- |
| ORDER_ID      | identifier  | Primary identity                                |
| MIN_AMOUNT    | number      | Lower amount boundary                           |
| MAX_AMOUNT    | number      | Upper amount boundary                           |
| ORDER_AMOUNT  | number      | Amount constrained by MIN_AMOUNT and MAX_AMOUNT |
| CUSTOMER_TYPE | categorical | STANDARD or PREMIUM                             |
| DISCOUNT      | number      | Discount percentage                             |

### Entity

`CUSTOMER`

### Fields

| Field         | Type        | Semantic / Behavior    |
| ------------- | ----------- | ---------------------- |
| CUSTOMER_ID   | identifier  | Primary identity       |
| COUNTRY       | categorical | Country classification |
| CUSTOMER_TYPE | categorical | STANDARD or PREMIUM    |

The experiment does not require a large dataset because the primary validation target is the constraint specification itself.

---

## 5. Experiment Configuration

Constraints will be represented explicitly rather than embedded inside generation code.

Example:

```json
{
  "constraints": [
    {
      "id": "C001",
      "type": "range",
      "field": "MIN_AMOUNT",
      "operator": ">=",
      "value": 100
    },
    {
      "id": "C002",
      "type": "range",
      "field": "MAX_AMOUNT",
      "operator": "<=",
      "value": 5000
    }
  ]
}
```

Cross-field constraints will also be represented explicitly.

Example:

```json
{
  "id": "C003",
  "type": "cross_field",
  "left": "MIN_AMOUNT",
  "operator": "<=",
  "right": "MAX_AMOUNT"
}
```

The experiment will then introduce conflicting constraints.

Example:

```json
{
  "id": "C004",
  "type": "range",
  "field": "MIN_AMOUNT",
  "operator": ">=",
  "value": 6000
}
```

Combined with:

```text
MAX_AMOUNT <= 5000
MIN_AMOUNT <= MAX_AMOUNT
```

this produces an unsatisfiable constraint set.

---

## 6. Conflict Categories

The experiment will evaluate several classes of conflicts.

### 6.1 Direct Numeric Conflict

Example:

```text
MIN_AMOUNT >= 2000
MIN_AMOUNT <= 1000
```

Expected:

```text
CONFLICT
```

---

### 6.2 Boundary Conflict

Example:

```text
DISCOUNT >= 20
DISCOUNT <= 10
```

Expected:

```text
CONFLICT
```

---

### 6.3 Cross-Field Conflict

Example:

```text
MIN_AMOUNT <= MAX_AMOUNT
MIN_AMOUNT >= 5000
MAX_AMOUNT <= 3000
```

Expected:

```text
CONFLICT
```

The individual range constraints may appear valid, but their combination is impossible.

---

### 6.4 Categorical Conflict

Example:

```text
CUSTOMER_TYPE = PREMIUM
CUSTOMER_TYPE = STANDARD
```

Expected:

```text
CONFLICT
```

---

### 6.5 Conditional Conflict

Example:

```text
IF CUSTOMER_TYPE = PREMIUM
THEN DISCOUNT >= 20
```

and:

```text
IF CUSTOMER_TYPE = PREMIUM
THEN DISCOUNT <= 10
```

Expected:

```text
CONFLICT
```

The conflict exists only within the PREMIUM condition.

---

### 6.6 Compatible Constraints

Example:

```text
MIN_AMOUNT >= 100
MIN_AMOUNT <= 5000
MIN_AMOUNT <= MAX_AMOUNT
```

Expected:

```text
COMPATIBLE
```

This case is essential because the experiment must demonstrate that the detector does not report false conflicts.

---