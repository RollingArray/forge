# Experiment 008: Domain vs Generation Strategy

**Status:** Planned  
**Experiment Type:** Foundational / Structural  
**FORGE Area:** Specification / Generation  
**Objective:** Determine whether domain information and value-generation strategy can be represented as separate concerns in the FORGE specification.

---

## 1. Research Question

Can FORGE independently represent:

1. The set of values that are valid for a field, and
2. The mechanism used to select or generate a value from that set?

---

## 2. Hypothesis

Domain information and generation strategy should be treated as separate concepts.

A domain describes the possible or valid values for a field.

A generation strategy describes how FORGE should select or produce a value using that domain.

For example:

```text
Domain:
    ["US", "IN", "DE", "FR"]

Generation Strategy:
    uniform
```

should be conceptually different from:

```text
Domain:
    ["US", "IN", "DE", "FR"]

Generation Strategy:
    weighted
```

Yes, agreed. We should **keep the established README structure as the baseline**. As the experiments mature, we can add sections where the research genuinely needs them, but we should not keep reinventing the format.

For Experiment 008, let's therefore use the same structure as 001-006 and 007, with the content adapted to the actual research question.

I would make the README exactly like this:

````markdown
# Experiment 008: Domain vs Generation Strategy

**Status:** Planned  
**Experiment Type:** Foundational / Structural  
**FORGE Area:** Specification / Generation  
**Objective:** Determine whether domain information and value-generation strategy can be represented as separate concerns in the FORGE specification.

---

## 1. Research Question

Can FORGE independently represent:

1. The set of values that are valid for a field, and
2. The mechanism used to select or generate a value from that set?

---

## 2. Hypothesis

Domain information and generation strategy should be treated as separate concepts.

A domain describes the possible or valid values for a field.

A generation strategy describes how FORGE should select or produce a value using that domain.

For example:

```text
Domain:
    ["US", "IN", "DE", "FR"]

Generation Strategy:
    uniform
````

should be conceptually different from:

```text
Domain:
    ["US", "IN", "DE", "FR"]

Generation Strategy:
    weighted
```

The same domain should therefore be reusable with multiple generation strategies without redefining the domain itself.

The hypothesis will be considered supported if:

* The same domain can be reused by multiple generation strategies.
* Changing the generation strategy changes the generated behavior without changing the domain.
* The generated values remain within the declared domain.
* A fixed-value strategy can use a domain containing multiple values.
* The generator implementation does not require domain-specific knowledge.

The hypothesis will be rejected if domain definitions and generation strategies cannot be cleanly separated without introducing unnecessary coupling or duplication.

---

## 3. Scope

This experiment will generate values from a common domain using multiple generation strategies.

The experiment will deliberately use a small, domain-neutral categorical field.

### Included

* Explicit domain definition
* Domain validation
* Fixed-value generation
* Uniform domain selection
* Weighted domain selection
* Random domain selection
* Reuse of the same domain across strategies
* Strategy-specific configuration
* Generated-value validation
* Comparison of generated behavior

### Excluded

* Real production data
* Machine Learning
* Deep Learning
* Large Language Models
* Statistical inference
* Cross-field correlation
* Cross-entity relationships
* Complex business rules
* Domain discovery
* Domain inference from real datasets
* External domain repositories
* Advanced statistical validation

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a generic `CUSTOMER` entity.

The `COUNTRY` domain will be reused across multiple fields, with each field using a different generation strategy.

The domain itself will remain independent of the strategy used to generate values.

### Entity

`CUSTOMER`

### Fields

| Field            | Type        | Semantic / Behavior              |
| ---------------- | ----------- | -------------------------------- |
| CUSTOMER_ID      | identifier  | Sequential identifier            |
| COUNTRY_FIXED    | categorical | Fixed value selected from domain |
| COUNTRY_UNIFORM  | categorical | Uniform selection from domain    |
| COUNTRY_WEIGHTED | categorical | Weighted selection from domain   |
| COUNTRY_RANDOM   | categorical | Random selection from domain     |

Shared domain:

```text
["US", "IN", "DE", "FR"]
```

---

## 5. Experiment Configuration

The specification will explicitly separate the domain from the generation strategy.

The domain describes the valid values:

```text
COUNTRY
    ├── US
    ├── IN
    ├── DE
    └── FR
```

The generation strategy describes how values are selected:

```text
COUNTRY
    │
    ├── fixed
    ├── uniform
    ├── weighted
    └── random
```

Example:

```json
{
  "domains": {
    "COUNTRY": {
      "type": "categorical",
      "values": [
        "US",
        "IN",
        "DE",
        "FR"
      ]
    }
  },

  "entities": {
    "CUSTOMER": {
      "record_count": 1000,

      "fields": {
        "CUSTOMER_ID": {
          "type": "identifier",
          "length": 10,
          "prefix": "CUS",
          "nullable": false
        },

        "COUNTRY_FIXED": {
          "type": "categorical",
          "domain": "COUNTRY",
          "generation": {
            "strategy": "fixed",
            "value": "US"
          },
          "nullable": false
        },

        "COUNTRY_UNIFORM": {
          "type": "categorical",
          "domain": "COUNTRY",
          "generation": {
            "strategy": "uniform"
          },
          "nullable": false
        },

        "COUNTRY_WEIGHTED": {
          "type": "categorical",
          "domain": "COUNTRY",
          "generation": {
            "strategy": "weighted",
            "weights": [
              0.50,
              0.30,
              0.15,
              0.05
            ]
          },
          "nullable": false
        },

        "COUNTRY_RANDOM": {
          "type": "categorical",
          "domain": "COUNTRY",
          "generation": {
            "strategy": "random"
          },
          "nullable": false
        }
      }
    }
  }
}
```

The architectural distinction being tested is:

```text
Domain
    =
what values are valid

Generation Strategy
    =
how a value is selected
```

---

## 6. Generation Strategies

The experiment will evaluate four strategies.

### Fixed

The generator always returns a declared value.

Example:

```text
Domain:
    ["US", "IN", "DE", "FR"]

Strategy:
    fixed

Value:
    US
```

Expected result:

```text
US
US
US
US
...
```

The fixed value must belong to the declared domain.

---

### Uniform

Every value in the domain has equal probability.

Example:

```text
US    25%
IN    25%
DE    25%
FR    25%
```

The generated values must remain within the declared domain.

---

### Weighted

The domain remains unchanged, but selection probabilities are supplied separately.

Example:

```text
US    50%
IN    30%
DE    15%
FR     5%
```

The weights describe selection behavior.

They do not redefine the domain.

---

### Random

The generator selects a value from the domain without an explicitly declared weighting.

The experiment will determine whether `random` is meaningfully different from `uniform`, or whether it should simply be treated as another form of domain sampling.

This distinction is intentionally left open for the experiment to resolve.

---