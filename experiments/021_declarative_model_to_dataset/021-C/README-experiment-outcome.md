# Experiment 021-C: Declarative Constraint-Aware Model to Dataset

## 1. What were we trying to prove?

**In simple terms**

021-A proved that FORGE can turn a declarative model into datasets.

021-B proved that FORGE can understand relationships between those datasets.

The next question was:

> **Can FORGE use constraints declared in the specification to generate data that satisfies those constraints, while still preserving the relational model?**

The important architectural requirement is that the constraints must come from the specification.

FORGE should not contain hard-coded rules such as:

```text
if CUSTOMER_SCORE >= 80:
    CUSTOMER_TYPE = PREMIUM
```

Instead, the specification describes the rule and the generic runtime interprets it.

---

## 2. What did we actually do?

We used a declarative relational model containing:

* 2 entities
* 7 fields
* 1 relationship
* 4 declarative constraints
* 100 CUSTOMER records
* 50 PRODUCT records
* Seed = `42`
* Scenario = `NORMAL`

The relational model remained:

```text
CUSTOMER
    |
    | CUSTOMER_ID
    |
    +--------> PRODUCT.CUSTOMER_ID
                 [1:N]
```

We then introduced declarative constraints such as:

```text
CUSTOMER_SCORE
    must be between 0 and 100
```

```text
PRODUCT_PRICE
    must be between 10 and 1000
```

and a conditional rule:

```text
CUSTOMER_TYPE = PREMIUM
        implies
CUSTOMER_SCORE >= 80
```

The generation flow became:

```text
Specification
      ↓
Specification validation
      ↓
Relationship discovery
      ↓
Constraint discovery
      ↓
Generation planning
      ↓
Candidate generation
      ↓
Constraint evaluation
      ↓
Relationship resolution
      ↓
Final validation
      ↓
CSV datasets
```

The runtime does not modify an invalid record after generation.

Instead, an invalid candidate is rejected and another candidate is generated.

---

## 3. What happened?

**The experiment completed successfully.**

The specification was successfully interpreted and the relational model was generated.

The expected validation areas are:

```text
Specification structure          PASS

Dataset structure                PASS

Population counts                PASS

Field presence                   PASS

Identity uniqueness              PASS

Constraint integrity             PASS

Relationship configuration       PASS

Referential integrity            PASS

Reproducibility                  PASS

Seed sensitivity                 PASS

Entity-order independence        PASS

Field-order independence         PASS
```

**Overall: PASS**

The important outcome is that the generated dataset remained both:

1. **Relationally valid**
2. **Constraint valid**

---

## 4. What does that actually mean?

This experiment moves FORGE another step away from custom dataset-generation code.

Previously:

```text
Declarative Model
      ↓
Relationships
      ↓
Relational Dataset
```

Now:

```text
Declarative Model
      ↓
Relationships
      +
Constraints
      ↓
Constraint-aware
Relational Dataset
```

The specification is becoming a much more complete description of the dataset we want.

It describes not only:

> "What fields exist?"

and:

> "How are entities connected?"

but also:

> "What values are allowed?"

and:

> "What conditions must hold between values?"

---

## 5. Why is this important?

This is directly aligned with the FORGE objective.

A domain owner should eventually be able to describe a model like:

```text
I have these entities.

I have these fields.

These fields are related.

These values must stay within these limits.

If this condition is true, another condition must hold.
```

The domain owner should not have to translate those requirements into Python.

The intended architecture is:

```text
Domain Owner
      |
      | Declarative specification
      v
FORGE Model
      |
      v
Generic Generation Engine
      |
      v
Constraint-valid Dataset
```

This means the specification is increasingly becoming the **contract between domain intent and generated data**.

---

## 6. What did we learn?

The most important learning from 021-C is:

> **Declarative constraints can be interpreted as part of the model-to-dataset generation process rather than being implemented as domain-specific generation code.**

We also reinforced an important FORGE design principle:

### Generate correctly rather than repair later

The intended behavior is:

```text
Generate candidate
       ↓
Evaluate constraints
       ↓
     Valid?
     /    \
   YES     NO
    |       |
    v       v
 Accept   Reject
            |
            v
        Generate again
```

The experiment therefore keeps the distinction between:

```text
Generation
```

and:

```text
Post-generation repair
```

clear.

That distinction will become increasingly important as FORGE handles more complex specifications.

---

## 7. What has NOT been proven yet?

021-C does **not** prove that FORGE can handle every type of constraint.

We have not yet proven:

* Complex multi-entity constraints
* Large constraint dependency graphs
* Constraints involving derived fields
* Statistical relationships combined with constraints
* Complex conditional generation
* Constraint conflict diagnosis
* Impossible specification explanation
* Large-scale constraint performance
* Complex many-to-many relational constraints

Those capabilities should remain separate experiments.

---

## 8. Architectural outcome

### Before 021-C

We had validated:

```text
021-A

Declarative Model
      ↓
Dataset
```

and:

```text
021-B

Declarative Relational Model
      ↓
Related Datasets
      ↓
Referential Integrity
```

### After 021-C

We have experimentally validated:

```text
Declarative Relational Model
          ↓
Relationship Discovery
          ↓
Constraint Discovery
          ↓
Generation Planning
          ↓
Constraint-aware Generation
          ↓
Relationship Resolution
          ↓
Validated Dataset
```

This is an important architectural step because constraints are now part of the **generation contract**, not an external validation step only.

---

## 9. Resulting FORGE capability

> **FORGE can interpret declarative constraints as part of a relational model and generate a dataset that satisfies those constraints while preserving the declared relationships.**

The generation behavior remains driven by the specification rather than by knowledge of the domain encoded in Python.

---

## 10. Evidence

**Experiment:** `021-C`

**Result:** `PASS`

**Model:** `constraint_aware_relational_model`

**Specification version:** `1.0.0`

**Vocabulary version:** `1.0`

**Seed:** `42`

**Scenario:** `NORMAL`

**Entities:** `2`

**Relationships:** `1`

**Constraints:** `4`

**Generation order:**

```text
CUSTOMER → PRODUCT
```

**Relationship:**

```text
CUSTOMER.CUSTOMER_ID
        →
PRODUCT.CUSTOMER_ID
```

**Cardinality:** `1:N`

**Relationship-managed fields:** `1`

**Total records:** `150`

**Dataset format:** `CSV`

**Constraint integrity:** `PASS`

**Referential integrity:** `PASS`

**Reproducibility:** `PASS`

**Seed sensitivity:** `PASS`

**Entity-order independence:** `PASS`

**Field-order independence:** `PASS`

**No post-generation repair:** `PASS`

**Output datasets:**

```text
output/dataset/CUSTOMER.csv
output/dataset/PRODUCT.csv
```

**Manifest:**

```text
output/generation_manifest.json
```

**Experiment results:**

```text
output/constraint_generation_results.json
```

---

## 11. One-line takeaway

> **021-C proved that FORGE can extend a declarative relational model with constraints and use those constraints during generic dataset generation, producing a relational dataset that satisfies both its relationships and declared rules.**
