# Experiment 016: Statistical Generation Validation

**Status:** Planned  
**Experiment Type:** Statistical / Validation  
**FORGE Area:** Statistical Validation  
**Objective:** Determine whether FORGE can quantitatively validate that generated data conforms sufficiently to its declared statistical generation behavior.

---

## 1. Research Question

Given a declared statistical generation behavior, can FORGE determine whether the generated dataset conforms sufficiently to the expected statistical characteristics?

For example:

```text
Declared:

COUNTRY
    US = 50%
    IN = 30%
    DE = 15%
    FR = 5%

Generated:

COUNTRY
    US = 49.7%
    IN = 30.4%
    DE = 14.8%
    FR = 5.1%

Validation:

    PASS
````

The experiment will determine what statistical measurements and tolerance mechanisms are useful for validating synthetic enterprise data.

---

## 2. Hypothesis

A generated dataset can be validated against declared statistical expectations using measurable statistical characteristics and configurable tolerances.

The generator should be able to:

* Capture declared statistical expectations.
* Calculate observed statistics from generated data.
* Compare observed values against expected values.
* Apply configurable tolerances.
* Distinguish acceptable variation from meaningful deviation.
* Produce a clear PASS / WARN / FAIL result.
* Validate both categorical and numeric generation behavior.

The hypothesis should be considered supported if the validation mechanism can correctly identify:

* Data that conforms to the declared distribution.
* Data that differs materially from the declared distribution.
* Expected sampling variation in finite datasets.
* Numeric values that fall outside declared statistical boundaries.

The experiment will not assume that observed statistics must exactly equal declared statistics.

---

## 3. Scope

This experiment will evaluate statistical validation of generated data using controlled categorical and numeric distributions.

The experiment will compare declared statistical expectations against observed characteristics from generated datasets.

### Included

* Categorical distribution validation
* Weighted categorical distribution validation
* Numeric range validation
* Mean validation
* Median validation
* Standard deviation validation
* Percentile validation
* Configurable tolerances
* Sampling variation
* PASS / WARN / FAIL classification
* Statistical validation evidence
* Comparison across different record counts

### Excluded

* Correlation validation
* Cross-field statistical relationships
* Statistical dependency validation
* Full validation framework
* Constraint validation
* Referential integrity validation
* Automatic distribution discovery
* Advanced hypothesis testing
* Production-scale performance testing

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a domain-neutral customer and order model.

The dataset will contain fields representing both categorical and numeric generation behavior.

### Entity

`CUSTOMER`

### Fields

| Field         | Type        | Semantic / Behavior               |
| ------------- | ----------- | --------------------------------- |
| CUSTOMER_ID   | identifier  | Unique customer identity          |
| COUNTRY       | categorical | Weighted categorical distribution |
| CUSTOMER_TYPE | categorical | Weighted categorical distribution |

### Entity

`ORDER`

### Fields

| Field    | Type       | Semantic / Behavior          |
| -------- | ---------- | ---------------------------- |
| ORDER_ID | identifier | Unique order identity        |
| AMOUNT   | number     | Uniform numeric distribution |
| DISCOUNT | number     | Bounded numeric distribution |

The experiment will use sufficiently large datasets to observe the effect of sample size on statistical validation.

---

## 5. Experiment Configuration

The specification will contain both generation behavior and statistical expectations.

Example:

```json
{
  "field": {
    "type": "categorical",
    "generation": {
      "strategy": "weighted",
      "weights": {
        "US": 0.50,
        "IN": 0.30,
        "DE": 0.15,
        "FR": 0.05
      }
    },
    "validation": {
      "distribution_tolerance": 0.03
    }
  }
}
```

For numeric generation:

```json
{
  "field": {
    "type": "number",
    "generation": {
      "strategy": "uniform",
      "min": 100,
      "max": 10000
    },
    "validation": {
      "mean_tolerance": 150,
      "median_tolerance": 150,
      "percentile_tolerance": 200
    }
  }
}
```

The experiment will investigate whether statistical expectations should be expressed alongside generation metadata.

---

## 6. Statistical Characteristics

The experiment will initially evaluate the following characteristics.

### 6.1 Categorical Distribution

For a weighted categorical field:

```text
Expected:

US = 50%
IN = 30%
DE = 15%
FR = 5%
```

The validator will calculate:

```text
Observed percentage
Expected percentage
Absolute difference
Tolerance
Result
```

Example:

```text
US
    expected = 50.00%
    observed = 49.70%
    difference = 0.30%
    tolerance = 3.00%
    result = PASS
```

---

### 6.2 Numeric Range

For:

```text
ORDER.AMOUNT
```

with:

```text
minimum = 100
maximum = 10000
```

the validator will verify that generated values remain within the declared bounds.

Expected:

```text
Minimum >= 100
Maximum <= 10000
```

---

### 6.3 Mean

The observed mean will be compared against the expected mean.

For a uniform distribution:

```text
Expected mean:

(min + max) / 2
```

For example:

```text
100 + 10000
---------------- = 5050
       2
```

The observed mean will be evaluated using a configurable tolerance.

---

### 6.4 Median

The observed median will be compared against the expected median.

For a symmetric uniform distribution, the expected median is also approximately the midpoint.

The experiment will determine whether median provides useful additional evidence beyond the mean.

---

### 6.5 Standard Deviation

The observed standard deviation will be compared against the expected statistical behavior of the declared distribution.

This will help determine whether matching only the mean is insufficient.

For a uniform distribution:

```text
σ = (b - a) / √12
```

The observed value will be compared against the theoretical expectation.

---

### 6.6 Percentiles

The validator will calculate selected percentiles:

```text
P05
P25
P50
P75
P95
```

These provide a more complete view of the generated numeric distribution.

The experiment will determine whether percentile validation provides useful evidence for synthetic enterprise data.

---

## 7. Sampling Variation

A key objective of the experiment is to demonstrate that statistical validation must account for sample size.

For example:

```text
1,000 records
```

may produce:

```text
US = 48.9%
```

while:

```text
100,000 records
```

may produce:

```text
US = 50.1%
```

Both may be acceptable.

Therefore, the validator should not require:

```text
observed == expected
```

Instead:

```text
observed
    ↓
difference
    ↓
tolerance
    ↓
validation result
```

The experiment will evaluate multiple record counts to observe this behavior.

---

## 8. Validation Result Model

The experiment will evaluate a three-state result model:

```text
PASS
WARN
FAIL
```

### PASS

Observed statistics are within the configured acceptable tolerance.

### WARN

Observed statistics are outside the preferred tolerance but may still be explained by sampling variation or a non-critical deviation.

### FAIL

Observed statistics materially violate the declared expectation.

The exact thresholds will be defined in the experiment specification.

---