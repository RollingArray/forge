# Experiment 021-A: Declarative Model to Dataset

## 1. What were we trying to prove?

**In simple terms**

Experiment 020 established that FORGE can understand and validate a declarative description of the data we want.

The next question is much more important:

> **Can FORGE take that declarative model and actually produce a dataset from it?**

The intended flow is:

```text
Declarative Model
       ↓
      FORGE
       ↓
Actual Synthetic Dataset
````

We specifically wanted to avoid writing custom generation code for `CUSTOMER` or `PRODUCT`.

The model should describe what we want, and the generic FORGE generation logic should determine how to create it.

---

## 2. What did we actually do?

We gave FORGE a domain-neutral `specification.json`.

The specification described:

* 2 entities
* Population sizes
* 7 fields
* Field types
* Sequential identities
* Random numerical generation
* Categorical generation
* Boolean generation
* Declared numerical ranges
* Declared categorical values

The model contained:

```text
CUSTOMER
  ├── CUSTOMER_ID
  ├── CUSTOMER_SCORE
  ├── CUSTOMER_TYPE
  └── IS_ACTIVE

PRODUCT
  ├── PRODUCT_ID
  ├── PRODUCT_PRICE
  └── PRODUCT_TYPE
```

The requested population was:

```text
CUSTOMER    100 records

PRODUCT      50 records

TOTAL        150 records
```

We also used a fixed random seed:

```text
Seed:      42
Scenario:  NORMAL
```

The experiment then asked the generic generator to execute the specification.

---

## 3. What happened?

**Everything passed.**

```text
Specification validity          PASS

Dataset generation              PASS

Dataset structure               PASS

Population counts               PASS

Field presence                  PASS

Identity uniqueness             PASS

Declared ranges                 PASS

Categorical values              PASS

Reproducibility                 PASS

Seed sensitivity                PASS
```

**Overall: PASS**

FORGE successfully transformed the declarative model into an actual dataset containing:

```text
CUSTOMER    100 records

PRODUCT      50 records

TOTAL        150 records
```

---

## 4. What did we actually generate?

FORGE produced real dataset artifacts rather than simply reporting that generation was possible.

Example CUSTOMER record:

```text
{
  "CUSTOMER_ID": "CUS-1",
  "CUSTOMER_SCORE": 89.1451,
  "CUSTOMER_TYPE": "STANDARD",
  "IS_ACTIVE": true
}
```

Example PRODUCT record:

```text
{
  "PRODUCT_ID": "PRD-1",
  "PRODUCT_PRICE": 337.83,
  "PRODUCT_TYPE": "STANDARD"
}
```

The generated dataset was written to:

```text
output/dataset.json
```

Entity-level CSV files were also produced.

This is important because 021 moves the FORGE experiments from validating individual capabilities to producing an actual data artifact.

---

## 5. Did the generated data follow the model?

**Yes.**

FORGE independently checked the generated dataset against the declarations in the specification.

### Dataset structure

The expected entities and fields were present.

**Result: PASS**

### Population

The requested populations were generated.

```text
CUSTOMER    100

PRODUCT      50
```

**Result: PASS**

### Identity

Generated identifiers were unique.

**Result: PASS**

### Numerical ranges

Generated numerical values remained within the ranges declared by the specification.

**Result: PASS**

### Categorical values

Generated categorical values came only from the values declared in the specification.

**Result: PASS**

In simple terms:

> **FORGE did not just generate data. It generated data that followed the model it was given.**

---

## 6. Is generation reproducible?

**Yes.**

The experiment generated the dataset using seed `42`.

It then generated the same model again using the same seed.

The resulting datasets were identical.

```text
Same specification
       +
Same seed
       ↓
Same dataset
```

**Reproducibility: PASS**

This is important for engineering use cases where a dataset may need to be recreated later for debugging, testing, or validation.

---

## 7. Does changing the seed change the data?

**Yes.**

The experiment generated the same specification using a different seed.

The stochastic values changed.

```text
Seed 42
   ↓
Dataset A

Seed 43
   ↓
Dataset B

Dataset A ≠ Dataset B
```

**Seed sensitivity: PASS**

This demonstrates that the generated values are actually driven by controlled randomness rather than being fixed example data.

---

## 8. What does this actually mean?

This is the first important result of Experiment 021.

Experiment 020 demonstrated that FORGE had the individual capabilities needed to generate different types of values.

Experiment 021-A demonstrates that those capabilities can now be driven by a **model**.

The important transition is:

```text
020

Individual generation capabilities
       ↓
Can the mechanisms work?
```

to:

```text
021-A

Declarative model
       ↓
Generic FORGE execution
       ↓
Actual dataset
```

That is a significant architectural step.

---

## 9. Why is this important?

The goal of FORGE is not to build a collection of dataset-specific generators.

We do not want:

```text
CUSTOMER dataset
       ↓
custom Python generator

ORDER dataset
       ↓
different custom Python generator

PLM dataset
       ↓
another custom Python generator

MES dataset
       ↓
another custom Python generator
```

The direction we are testing is:

```text
Domain Owner
      ↓
Describe the model
      ↓
Declarative specification
      ↓
FORGE
      ↓
Synthetic dataset
```

The domain owner describes **what the data should look like and how it should behave**.

FORGE provides the generic machinery to turn that description into data.

That is the core hypothesis we are beginning to test.

---

## 10. What did we learn?

The most important learning from 021-A is:

> **A domain-neutral declarative model can be executed by generic FORGE logic to produce an actual synthetic dataset.**

We also learned that the specification can remain separate from the execution mechanism.

The specification describes:

```text
What exists
What fields exist
How fields behave
How many records are required
```

The generator is responsible for:

```text
How to execute the model
How to create the records
How to validate the result
```

This separation is important if FORGE is eventually going to support models from very different domains without embedding domain knowledge into the generator itself.

---

## 11. What has NOT been proven yet?

This experiment is intentionally small.

It does **not** yet prove that FORGE can correctly generate:

* Relationships between entities
* Foreign-key references
* One-to-many relationships
* Many-to-many relationships
* Cross-field constraints
* Conditional rules
* Derived fields
* Dependency chains
* Statistical relationships
* Complex relational models
* Scenario-specific datasets
* Large-scale datasets
* Realistic domain behavior

It also does not prove that the generated data is realistic for any particular engineering domain.

That is intentional.

We are still testing the **generic model-to-data mechanism**, not domain realism.

---

## 12. Architectural outcome

### Before 021-A

We had:

```text
Declarative specification
       ↓
FORGE generation capabilities
```

We had demonstrated that many individual capabilities worked.

### After 021-A

We now have:

```text
Declarative model
       ↓
Generic execution
       ↓
Actual dataset
       ↓
Independent validation
```

The model is no longer just a description that can be validated.

It can now drive execution.

---

## 13. Resulting FORGE capability

> **FORGE can take a simple domain-neutral declarative model and generate an actual synthetic dataset from it without requiring entity-specific generation code.**

This is the first concrete model-to-data capability of Experiment 021.

---

## 14. Evidence

**Experiment:** `021-A`

**Result:** `PASS`

**Entities:** `2`

**Fields:** `7`

**CUSTOMER records:** `100`

**PRODUCT records:** `50`

**Total records:** `150`

**Specification version:** `1.0.0`

**Vocabulary version:** `1.0`

**Seed:** `42`

**Scenario:** `NORMAL`

**Reproducibility:** `PASS`

**Seed sensitivity:** `PASS`

**Dataset validation:** `PASS`

**Output dataset:** `dataset.json`

**Output manifest:** `generation_manifest.json`

**Output results:** `model_to_dataset_results.json`

---

## 15. What should we investigate next?

The current model contains two independent entities.

That is useful, but a real relational model becomes interesting when entities are connected.

The next question should therefore be:

> **Can the same declarative model describe relationships between entities, and can FORGE generate data while preserving those relationships?**

That moves us from:

```text
CUSTOMER

PRODUCT
```

to something like:

```text
CUSTOMER
    │
    │
    └──── ORDER
             │
             └──── PRODUCT
```

without changing the fundamental idea:

```text
Describe the model
       ↓
FORGE
       ↓
Generate the dataset
```
