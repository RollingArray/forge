### Experiment

**021-D - Declarative Derived & Conditional Model to Dataset**

### Status

**PASS**

### Objective

Experiment 021-D validates that a declarative model containing derived fields, conditional fields, chained dependencies, relationships, and constraints can be interpreted by a generic FORGE generation engine and materialized as an actual relational dataset.

The experiment moves beyond structural, relational, and constraint-aware generation demonstrated in 021-A, 021-B, and 021-C.

The key question is:

> Can FORGE generate fields whose values depend on other fields, determine the correct generation order from those declarations, combine those behaviors with relationships and constraints, and produce a valid CSV dataset without entity-specific generation logic?

No generation logic for CUSTOMER or PRODUCT is embedded in the experiment code. The engine reads the model and its behavioral declarations from `specification.json`.

---

# 1. What This Experiment Adds

The progression of Experiment 021 is:

```text
021-A
Declarative Model → Dataset
        |
        v
021-B
+ Relationships
        |
        v
021-C
+ Constraints
        |
        v
021-D
+ Derived & Conditional Dependencies
        |
        v
021-E
+ Statistical Behavior
````

021-D introduces deterministic behavioral dependencies.

The experiment demonstrates three important forms of dependency:

1. A conditional field depending on another field.
2. A derived field depending on multiple fields.
3. A conditional field depending on a derived field.

---

# 2. Declarative Model

The experiment uses the following entities:

```text
CUSTOMER
PRODUCT
```

with populations:

```text
CUSTOMER: 100 records
PRODUCT:   50 records
```

There is one relationship:

```text
CUSTOMER.CUSTOMER_ID
        |
        | ONE_TO_MANY
        v
PRODUCT.CUSTOMER_ID
```

The specification contains:

```text
Entities:       2
Relationships:  1
Constraints:    4
Dependencies:   4
```

---

# 3. Declarative Behavioral Dependencies

The specification declares the following behavior.

## 3.1 Customer Status

`CUSTOMER_STATUS` is conditionally generated from `CUSTOMER_TYPE`.

Conceptually:

```text
CUSTOMER_TYPE
      |
      v
CUSTOMER_STATUS

if CUSTOMER_TYPE == PREMIUM
    CUSTOMER_STATUS = PRIORITY
else
    CUSTOMER_STATUS = STANDARD
```

The generation engine does not know what a CUSTOMER is or what these values mean.

It simply interprets the conditional declaration contained in the specification.

---

## 3.2 Product Total Value

`PRODUCT.TOTAL_VALUE` is derived from:

```text
UNIT_PRICE
QUANTITY
```

The specification declares:

```text
TOTAL_VALUE = UNIT_PRICE * QUANTITY
```

Therefore the engine must generate:

```text
UNIT_PRICE
QUANTITY
```

before it can generate:

```text
TOTAL_VALUE
```

---

## 3.3 Product Value Band

`PRODUCT.VALUE_BAND` depends on the derived `TOTAL_VALUE`.

The specification declares:

```text
if TOTAL_VALUE >= 1000
    VALUE_BAND = HIGH
else
    VALUE_BAND = STANDARD
```

This creates a chained dependency:

```text
UNIT_PRICE ─────┐
                |
                +----> TOTAL_VALUE ----> VALUE_BAND
                |
QUANTITY ───────┘
```

The important point is that the engine must discover this dependency rather than relying on the field declaration order.

---

# 4. Generation Architecture

The implemented execution flow is:

```text
Declarative specification
        |
        v
Specification validation
        |
        v
Relationship / constraint discovery
        |
        v
Field dependency discovery
        |
        v
Dependency-aware generation planning
        |
        v
Base + derived + conditional generation
        |
        v
Relationship resolution
        |
        v
Canonical dataset normalization
        |
        v
Independent dataset validation
        |
        v
CSV datasets
```

The engine therefore separates:

* what the model declares
* what must be generated first
* how values are generated
* how relationships are resolved
* how the final dataset is validated

---

# 5. Discovered Dependencies

The engine dynamically discovered:

```text
CUSTOMER.CUSTOMER_STATUS
    <- CUSTOMER_TYPE

PRODUCT.TOTAL_VALUE
    <- QUANTITY, UNIT_PRICE

PRODUCT.VALUE_BAND
    <- TOTAL_VALUE
```

The resulting generation plan was:

```text
CUSTOMER
    CREDIT_LIMIT
    CUSTOMER_ID
    CUSTOMER_TYPE
    CUSTOMER_STATUS

PRODUCT
    PRODUCT_ID
    QUANTITY
    UNIT_PRICE
    TOTAL_VALUE
    VALUE_BAND
```

The exact order of independent fields is not semantically important.

What matters is that every dependency is generated after its required source fields.

---

# 6. Relationship Resolution

The specification declares:

```text
CUSTOMER.CUSTOMER_ID
        |
        v
PRODUCT.CUSTOMER_ID
```

as a `ONE_TO_MANY` relationship.

`PRODUCT.CUSTOMER_ID` is therefore identified as a relationship-managed field.

It is not independently generated using a normal field-generation strategy.

Instead, the relationship resolver selects a valid CUSTOMER identifier for each PRODUCT record.

The generated sample demonstrates this:

```text
CUSTOMER_ID: CUST-1
CUSTOMER_TYPE: STANDARD
CREDIT_LIMIT: 4965.701177668842
CUSTOMER_STATUS: STANDARD
```

and:

```text
PRODUCT_ID: PROD-1
CUSTOMER_ID: CUST-10
UNIT_PRICE: 1587.3045966347258
QUANTITY: 2
TOTAL_VALUE: 3174.6091932694517
VALUE_BAND: HIGH
```

The derived value is consistent:

```text
1587.3045966347258 × 2
= 3174.6091932694517
```

and because:

```text
3174.6091932694517 >= 1000
```

the conditional value is:

```text
HIGH
```

---

# 7. Constraint Preservation

Four constraints are declared in the model:

```text
PRODUCT.UNIT_PRICE > 0

PRODUCT.QUANTITY > 0

PRODUCT.TOTAL_VALUE >= 0

CUSTOMER.CREDIT_LIMIT >= 1000
```

The generated dataset preserved all four constraints.

This is important because `TOTAL_VALUE` is not independently sampled.

It is produced from other generated fields:

```text
UNIT_PRICE
QUANTITY
       |
       v
TOTAL_VALUE
```

The constraint validator therefore verifies the final derived result rather than merely checking the source fields.

---

# 8. Initial Failure

The first execution of 021-D did not produce a clean PASS.

The result was:

```text
Dataset Structure                     PASS
Population Counts                     PASS
Field Presence                        FAIL
Identity Uniqueness                   PASS
Referential Integrity                 PASS
Constraint Preservation               PASS
Derived Field Correctness             PASS
Conditional Field Correctness         PASS
Chained Dependency Correctness        PASS
```

The failure was therefore not caused by:

* incorrect derived values
* incorrect conditional values
* broken dependencies
* broken relationships
* broken constraints
* incorrect populations

The problem was the ordering of fields in the in-memory record representation.

---

# 9. Failure Diagnosis

`PRODUCT.CUSTOMER_ID` is a relationship-managed field.

Normal field generation creates:

```text
PRODUCT_ID
UNIT_PRICE
QUANTITY
TOTAL_VALUE
VALUE_BAND
```

Relationship resolution subsequently adds:

```text
CUSTOMER_ID
```

to the record.

This initially resulted in an in-memory record whose field order differed from the order declared by the specification.

The specification declares:

```text
PRODUCT_ID
CUSTOMER_ID
UNIT_PRICE
QUANTITY
TOTAL_VALUE
VALUE_BAND
```

while the generated in-memory record initially appeared as:

```text
PRODUCT_ID
UNIT_PRICE
QUANTITY
TOTAL_VALUE
VALUE_BAND
CUSTOMER_ID
```

The values themselves were correct.

The CSV artifact was also correct because the CSV writer used the specification-defined field order.

The failure therefore exposed an important engine-level requirement:

> The declarative specification must define the canonical schema representation of the generated dataset, not merely the values that appear in the final file.

---

# 10. Correction

The engine was corrected by introducing a generic record normalization step after relationship resolution.

The normalization reads the field order directly from the specification and reconstructs every record using that declared order.

Conceptually:

```text
Generated record
      |
      v
Relationship resolution
      |
      v
Canonical field-order normalization
      |
      v
Specification-defined record
```

This does not change generated values.

It does not relax constraints.

It does not repair invalid business data.

It only restores the canonical representation declared by the model.

The validator was deliberately not weakened.

---

# 11. Final Validation

After the correction, the complete experiment produced:

```text
Specification validation:
  Declarative structure              PASS
```

```text
Dataset validation:
  Dataset Structure                  PASS
  Population Counts                  PASS
  Field Presence                     PASS
  Identity Uniqueness                PASS
  Referential Integrity              PASS
  Constraint Preservation            PASS
  Derived Field Correctness          PASS
  Conditional Field Correctness      PASS
  Chained Dependency Correctness     PASS
```

CSV artifact validation:

```text
Final CSV structure                  PASS
```

Determinism and independence validation:

```text
Same specification + same seed        PASS
Different seed changes stochastic data PASS
Entity declaration order does not change results PASS
Field declaration order does not change results PASS
```

Final experiment result:

```text
Specification validity:       PASS
Relational generation:        PASS
Derived-field correctness:    PASS
Conditional correctness:      PASS
Chained dependencies:         PASS
Constraint preservation:      PASS
Referential integrity:        PASS
CSV artifact validation:      PASS
Reproducibility:              PASS
Seed sensitivity:             PASS
Entity-order independence:    PASS
Field-order independence:     PASS

Relationships:                1
Relationship-managed fields:  1
Constraints:                  4
Dependencies:                4
Total records:                150

Overall:                      PASS
```

---

# 12. Generated Dataset

The experiment generated:

```text
CUSTOMER: 100 records
PRODUCT:   50 records

Total:    150 records
```

CSV artifacts:

```text
output/dataset/CUSTOMER.csv
output/dataset/PRODUCT.csv
```

Additional artifacts:

```text
output/generation_manifest.json
output/derived_conditional_generation_results.json
```

---

# 13. What This Experiment Proves

021-D establishes that the FORGE model-to-dataset boundary can execute deterministic behavioral dependencies declared in the model.

Specifically, the experiment demonstrates that FORGE can:

* discover dependencies from declarative generation rules
* construct a dependency-aware field generation plan
* generate source fields before dependent fields
* generate derived values from multiple source fields
* evaluate conditional generation rules
* execute chained dependencies
* combine derived and conditional behavior with relationships
* preserve declared constraints
* resolve relationship-managed fields
* maintain a canonical specification-defined dataset schema
* produce CSV datasets
* validate the generated artifacts independently
* reproduce results with the same specification and seed
* change stochastic values when the seed changes
* remain independent of entity declaration order
* remain independent of field declaration order

Most importantly, these behaviors are interpreted from the specification rather than implemented as logic specific to CUSTOMER or PRODUCT.

---

# 14. What This Experiment Does Not Prove

021-D intentionally does not introduce statistical behavior.

It does not yet validate:

* statistical distributions
* distribution parameters
* empirical distributions
* multi-field statistical relationships
* cross-entity statistical relationships
* scenario-specific statistical behavior
* statistical validation against target distributions

Those capabilities have already been explored independently in Experiment 020, but they are intentionally not part of this model-to-dataset stage.

The next model-to-dataset capability should therefore build on this foundation rather than mixing multiple new concerns into 021-D.

---

# 15. Architectural Significance

021-D strengthens the central FORGE architectural principle:

```text
Specification
      |
      v
Interpretation
      |
      v
Generation Planning
      |
      v
Dataset Generation
      |
      v
Independent Validation
```

The generator is not being written as a collection of rules for known entities.

Instead, the specification describes:

```text
entities
fields
generation behavior
relationships
constraints
dependencies
```

and the engine determines how those declarations must be executed.

This is a critical distinction for FORGE.

A new domain should require a new specification, not a new generator implementation.

---