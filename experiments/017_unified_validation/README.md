# Experiment 017: Unified Validation

**Status:** Planned  
**Experiment Type:** Validation / Structural / Relationship / Rule / Statistical  
**FORGE Area:** Validation  
**Objective:** Determine whether structural, relational, rule, population, and statistical validation can be evaluated through a single unified validation model.

---

## 1. Research Question

Can FORGE validate a generated dataset through a unified validation framework that evaluates multiple dimensions of data quality without treating each validation type as an isolated mechanism?

Specifically, can a single validation process identify and report:

- Structural validity
- Referential integrity
- Field-level constraints
- Cross-field constraints
- Population behavior
- Statistical conformity

while preserving the individual result of each validation category?

---

## 2. Hypothesis

FORGE should be able to evaluate different dimensions of generated-data quality through a common validation model while keeping the validation logic specific to each quality dimension.

The hypothesis is that validation should be treated as a first-class capability rather than being embedded independently inside individual generation mechanisms.

The expected model is:

```text
Generated Dataset
       │
       ▼
   Validation
       │
       ├── Structural
       ├── Relational
       ├── Constraint
       ├── Population
       └── Statistical
              │
              ▼
       Unified Result
````

The unified validation model should:

* Execute multiple validation categories against the same generated dataset.
* Preserve detailed results for each category.
* Distinguish PASS, WARN, and FAIL.
* Identify the affected entity, field, relationship, or rule.
* Produce an overall validation result.
* Avoid allowing one validation category to hide failures in another category.

The experiment intentionally does **not** assume that all validation types use the same underlying algorithm.

For example:

* Structural validation may use schema inspection.
* Relationship validation may use key/reference checks.
* Constraint validation may evaluate predicates.
* Population validation may compare observed population rates.
* Statistical validation may compare observed and expected distributions.

The commonality should be in the **validation model and reporting structure**, not necessarily in the implementation algorithm.

The hypothesis should be considered rejected if the validation categories require fundamentally incompatible result models or if combining them causes loss of meaningful validation information.

---

## 3. Scope

This experiment will generate a small multi-entity dataset containing intentionally testable structural, relational, constraint, population, and statistical characteristics and evaluate the resulting dataset through a unified validation process.

### Included

* Structural validation
* Primary-key validation
* Foreign-key / referential validation
* Cross-field constraint validation
* Population validation
* Statistical validation
* PASS / WARN / FAIL classification
* Category-level validation results
* Field / relationship / rule-level evidence
* Unified validation summary
* Overall validation result
* Intentionally valid and invalid datasets

### Excluded

* Advanced statistical hypothesis testing
* Confidence intervals
* Constraint conflict detection
* Automatic repair of invalid data
* Validation of complex temporal behavior
* Performance optimization
* Generation evidence / provenance

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a small CUSTOMER / ORDER model so that multiple validation dimensions can be demonstrated without introducing unnecessary domain complexity.

### Entity

`CUSTOMER`

### Fields

| Field         | Type        | Semantic / Behavior            |
| ------------- | ----------- | ------------------------------ |
| CUSTOMER_ID   | identifier  | Primary identity               |
| COUNTRY       | categorical | Declared weighted distribution |
| CUSTOMER_TYPE | categorical | Declared weighted distribution |
| EMAIL         | string      | Optional population            |

### Entity

`ORDER`

### Fields

| Field        | Type       | Semantic / Behavior                          |
| ------------ | ---------- | -------------------------------------------- |
| ORDER_ID     | identifier | Primary identity                             |
| CUSTOMER_ID  | identifier | Foreign key to CUSTOMER                      |
| START_DATE   | date       | Beginning of order period                    |
| END_DATE     | date       | Must not precede START_DATE                  |
| MIN_AMOUNT   | number     | Lower amount boundary                        |
| MAX_AMOUNT   | number     | Upper amount boundary                        |
| ORDER_AMOUNT | number     | Must remain within MIN_AMOUNT and MAX_AMOUNT |

---

## 5. Experiment Configuration

The specification will declare both generation behavior and validation expectations.

Example:

```json
{
  "validation": {
    "structural": {
      "enabled": true
    },
    "relational": {
      "enabled": true
    },
    "constraints": {
      "enabled": true
    },
    "population": {
      "enabled": true
    },
    "statistical": {
      "enabled": true
    }
  }
}
```

Individual validation rules will remain explicit.

Example:

```json
{
  "constraints": [
    {
      "id": "C001",
      "expression": "START_DATE <= END_DATE"
    },
    {
      "id": "C002",
      "expression": "MIN_AMOUNT <= MAX_AMOUNT"
    },
    {
      "id": "C003",
      "expression": "MIN_AMOUNT <= ORDER_AMOUNT <= MAX_AMOUNT"
    }
  ]
}
```

The relationship will be explicitly declared:

```json
{
  "relationships": [
    {
      "id": "R001",
      "parent": "CUSTOMER.CUSTOMER_ID",
      "child": "ORDER.CUSTOMER_ID",
      "cardinality": "N:1"
    }
  ]
}
```

Population behavior will also be declared:

```json
{
  "population": {
    "EMAIL": {
      "expected_rate": 0.80,
      "tolerance": 0.05
    }
  }
}
```

Statistical behavior will build on the findings from Experiment 016.

---

## 6. Experimental Approach

The experiment will evaluate at least two generated datasets.

### Dataset A: Valid Dataset

The generator will produce data intended to satisfy all declared validation expectations.

Expected result:

```text
Structural       PASS
Relational       PASS
Constraints      PASS
Population       PASS
Statistical      PASS

Overall           PASS
```

### Dataset B: Invalid Dataset

The experiment will intentionally introduce controlled violations.

Examples include:

* Invalid foreign-key reference
* Duplicate primary key
* Invalid date ordering
* Invalid amount relationship
* Population outside tolerance
* Statistical deviation

Expected result:

```text
Structural       FAIL / PASS
Relational       FAIL
Constraints      FAIL
Population       WARN / FAIL
Statistical      WARN / FAIL

Overall           FAIL
```

The purpose is to determine whether the unified validator can identify multiple independent problems simultaneously.

---

## 7. Validation Result Model

The experiment will evaluate whether a common result structure can represent different validation categories.

Conceptually:

```json
{
  "validation": {
    "structural": {
      "result": "PASS",
      "checks": []
    },
    "relational": {
      "result": "PASS",
      "checks": []
    },
    "constraints": {
      "result": "FAIL",
      "checks": []
    },
    "population": {
      "result": "PASS",
      "checks": []
    },
    "statistical": {
      "result": "PASS",
      "checks": []
    }
  },
  "overall_result": "FAIL"
}
```

Each individual check should retain sufficient evidence to understand why it passed or failed.

For example:

```json
{
  "id": "C001",
  "type": "constraint",
  "expression": "START_DATE <= END_DATE",
  "records_checked": 1000,
  "violations": 12,
  "result": "FAIL"
}
```

The exact result structure will be refined based on the experiment.

---

## 8. Validation Categories

### 8.1 Structural Validation

Verify:

* Required entities exist.
* Required fields exist.
* Field types are valid.
* Primary keys are populated.
* Primary keys are unique.

Example:

```text
CUSTOMER schema        PASS
ORDER schema           PASS
CUSTOMER_ID uniqueness PASS
ORDER_ID uniqueness    PASS
```

---

### 8.2 Relational Validation

Verify:

* Foreign keys reference existing parent records.
* Declared relationships are respected.
* Cardinality expectations are respected where applicable.

Example:

```text
ORDER.CUSTOMER_ID
        ↓
CUSTOMER.CUSTOMER_ID

Invalid references: 0
Result: PASS
```

---

### 8.3 Constraint Validation

Verify cross-field rules such as:

```text
START_DATE <= END_DATE

MIN_AMOUNT <= MAX_AMOUNT

MIN_AMOUNT <= ORDER_AMOUNT <= MAX_AMOUNT
```

The validator should report:

* Rule ID
* Records evaluated
* Violations
* Result

---

### 8.4 Population Validation

Verify whether optional fields are populated within their declared expectations.

Example:

```text
EMAIL

Expected population: 80%
Observed population: 82.4%
Tolerance:            5%

Result: PASS
```

---

### 8.5 Statistical Validation

Build on Experiment 016.

Verify:

* Categorical distribution
* Numeric range
* Mean
* Median
* Standard deviation
* Percentiles

The experiment should preserve the important finding from Experiment 016:

> Statistical validation may be sensitive to sample size.

---