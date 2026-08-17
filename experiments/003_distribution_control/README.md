# Experiment 003: Distribution-Controlled Generation

**Status:** Planned  
**Experiment Type:** Statistical  
**FORGE Area:** Specification / Generation  
**Objective:** Determine whether explicit statistical distributions can improve synthetic data realism without requiring access to real data.

---

## 1. Research Question

Can synthetic data exhibit predictable statistical characteristics when the expected distribution of values is explicitly defined in metadata, without learning those characteristics from real production data?

---

## 2. Hypothesis

A synthetic dataset can achieve meaningful statistical realism when the generation specification explicitly describes the expected distribution of values.

The generator should be able to represent:

- Uniform distributions
- Weighted categorical distributions
- Numeric distributions
- Bounded distributions
- Field population rates

The generated data will not exactly reproduce the specified distribution because generation is probabilistic. However, as the generated volume increases, the observed characteristics should converge toward the declared expectations.

The purpose of this experiment is to determine whether **statistical intent can become part of the generation specification**, rather than something that must be learned from an existing dataset.

---

## 3. Scope

This experiment will generate a synthetic dataset for a single generic entity.

The experiment will build on the metadata and field constraint concepts established in Experiments 001 and 002.

### Included

- Entity definition
- Field definition
- Basic data types
- Uniform categorical distribution
- Weighted categorical distribution
- Numeric distribution
- Numeric bounds
- Field population rate
- Configurable record volume
- Deterministic random seed
- Statistical observation of generated data
- Generation output

### Excluded

- Real production data
- Machine Learning
- Deep Learning
- Large Language Models
- Distribution inference from real data
- Cross-field correlation
- Cross-entity relationships
- Conditional distributions
- Complex business rules
- Domain-specific SAP, PLM, MES or ERP logic
- Advanced statistical similarity metrics

These capabilities will be explored in later experiments.

---

## 4. Initial Entity

The experiment will use a generic `CUSTOMER` entity.

Example fields:

| Field | Type | Statistical Behavior |
|---|---|---|
| CUSTOMER_ID | string | Sequential identifier |
| COUNTRY_UNIFORM | string | Uniform distribution |
| COUNTRY_WEIGHTED | string | Weighted categorical distribution |
| AGE | integer | Normal distribution with bounds |
| PHONE | string | 70% population rate |

The entity is intentionally domain-neutral.

---

## 5. Expected Output

The experiment should produce a dataset similar to:

```text
CUSTOMER_ID  COUNTRY_UNIFORM  COUNTRY_WEIGHTED  AGE  PHONE
-----------  ---------------  ----------------  ---  ----------
0000000001   US               US                 38   8472931045
0000000002   IN               US                 46   9182736451
0000000003   DE               IN                 41   7291836452
0000000004   FR               US                 52   <blank>
...