# Experiment 007: Reproducible Generation

**Status:** Planned  
**Experiment Type:** Foundational / Validation  
**FORGE Area:** Generation / Reproducibility  
**Objective:** Determine whether the same generation specification, configuration, and random seed can produce an identical synthetic dataset across repeated executions.

---

## 1. Research Question

Can FORGE guarantee that the same generation specification, configuration, and random seed produce the same synthetic dataset when the experiment is executed repeatedly?

---

## 2. Hypothesis

Synthetic data generation should be reproducible when the following inputs remain unchanged:

- Generation specification
- Generation configuration
- Random seed
- Generator implementation

Two executions using the same inputs should produce identical generated data.

Changing the random seed should produce a different dataset while preserving the same structural and statistical generation behavior.

The hypothesis will be considered supported if:

- The same specification and seed produce byte-for-byte identical output.
- Repeated executions produce identical validation results.
- Changing the seed produces different generated values.
- Changing the seed does not change the declared schema or generation constraints.
- Reproducibility can be demonstrated without relying on real production data.

The experiment will also determine whether the random seed must be controlled globally or whether individual generation operations require independent deterministic random streams.

---

## 3. Scope

This experiment will test deterministic and reproducible synthetic data generation using the generation capabilities established in earlier experiments.

### Included

- Metadata-driven generation
- Field constraints
- Categorical generation
- Numeric generation
- Configurable random seed
- Repeated generation using the same seed
- Generation using different seeds
- Byte-level output comparison
- Dataset comparison
- Structural validation
- Reproducibility validation
- Generated output comparison

### Excluded

- Real production data
- Machine Learning
- Deep Learning
- Large Language Models
- Statistical distribution inference
- Cross-field correlation
- Complex business rules
- Advanced relationship generation
- Distributed generation
- Parallel random number streams
- Cross-platform reproducibility
- Version-to-version reproducibility

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment will use a generic `CUSTOMER` entity.

The entity will intentionally reuse concepts already established in Experiments 001 through 003 so that reproducibility can be tested independently of introducing new generation behavior.

### Entity

`CUSTOMER`

### Fields

| Field | Type | Semantic / Behavior |
|---|---|---|
| CUSTOMER_ID | identifier | Deterministic sequential identifier |
| COUNTRY | categorical | Weighted categorical distribution |
| AGE | integer | Bounded numeric distribution |
| CUSTOMER_CODE | pattern | Pattern-constrained identifier |
| PHONE | string | Optional generated value |

The dataset will remain domain-neutral.

---

## 5. Experiment Configuration

The generation specification will contain the entity metadata and generation behavior.

The random seed will be explicitly declared as part of the generation configuration.

Example:

```json
{
  "generation": {
    "seed": 42,
    "record_count": 100
  },

  "entities": {
    "CUSTOMER": {
      "fields": {
        "CUSTOMER_ID": {
          "type": "identifier",
          "length": 10,
          "prefix": "CUS"
        },
        "COUNTRY": {
          "type": "categorical",
          "values": [
            "US",
            "IN",
            "DE",
            "FR"
          ],
          "distribution": {
            "type": "weighted",
            "weights": [
              0.50,
              0.30,
              0.15,
              0.05
            ]
          }
        },
        "AGE": {
          "type": "integer",
          "min": 18,
          "max": 80
        },
        "CUSTOMER_CODE": {
          "type": "pattern",
          "pattern": "CUS-#####"
        },
        "PHONE": {
          "type": "string",
          "min_length": 10,
          "max_length": 10,
          "population_rate": 0.80
        }
      }
    }
  }
}