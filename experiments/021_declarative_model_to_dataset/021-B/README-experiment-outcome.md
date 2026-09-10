# Experiment 021-B: Declarative Relational Model to Dataset

## 1. What were we trying to prove?

**In simple terms**

021-A proved that FORGE can take a declarative model and generate independent datasets.

The next question was:

> **Can FORGE understand relationships declared in the specification and use them to generate related datasets without any entity-specific code?**

For example:

```text
CUSTOMER
    |
    | CUSTOMER_ID
    |
    +--------> PRODUCT.CUSTOMER_ID
```

The important part is that FORGE should not need to know that `CUSTOMER` represents customers or that `PRODUCT` represents products.

The relationship should come entirely from the specification.

---

## 2. What did we actually do?

We extended the declarative model with one relationship:

```text
CUSTOMER.CUSTOMER_ID
        |
        | 1:N
        v
PRODUCT.CUSTOMER_ID
```

The model contained:

* 2 entities
* 7 total fields
* 1 relationship
* 100 CUSTOMER records
* 50 PRODUCT records
* Seed = `42`
* Scenario = `NORMAL`

The important architectural addition was the concept of a **relationship-managed field**.

```text
PRODUCT.CUSTOMER_ID
```

does not have its own random generation rule.

Instead, FORGE understands from the relationship that its value must come from:

```text
CUSTOMER.CUSTOMER_ID
```

The generation flow therefore became:

```text
Specification
     ↓
Specification validation
     ↓
Relationship discovery
     ↓
Generation planning
     ↓
Generate parent
     ↓
Generate child
     ↓
Resolve relationship fields
     ↓
Validate references
     ↓
Write CSV datasets
```

---

## 3. What happened?

**Everything passed.**

Specification validation:

```text
Declarative structure              PASS
```

Relationship:

```text
CUSTOMER.CUSTOMER_ID
        →
PRODUCT.CUSTOMER_ID
[1:N]
```

Generation plan:

```text
CUSTOMER -> PRODUCT
```

Relationship-managed field:

```text
PRODUCT.CUSTOMER_ID
```

Dataset validation:

```text
Dataset Structure                  PASS
Population Counts                  PASS
Field Presence                     PASS
Identity Uniqueness                PASS
Relationship Configuration         PASS
Referential Integrity              PASS
```

Reproducibility:

```text
Same specification + same seed       PASS
```

Seed sensitivity:

```text
Different seed changes stochastic data PASS
```

Entity-order independence:

```text
Entity declaration order does not change results PASS
```

**Overall: PASS**

---

## 4. What did FORGE actually generate?

FORGE generated two CSV datasets.

### CUSTOMER

```text
100 records
```

Example:

```text
CUSTOMER_ID,CUSTOMER_SCORE,CUSTOMER_TYPE,IS_ACTIVE

CUS-1,89.145...,STANDARD,true
```

### PRODUCT

```text
50 records
```

Example:

```text
PRODUCT_ID,PRODUCT_PRICE,PRODUCT_TYPE,CUSTOMER_ID

PRD-1,337.83,STANDARD,CUS-27
```

Notice the important part:

```text
PRODUCT.CUSTOMER_ID = CUS-27
```

`CUS-27` must already exist in:

```text
CUSTOMER.CUSTOMER_ID
```

That is what **referential integrity** means here.

FORGE did not simply generate a random customer ID.

It resolved the value from the generated parent dataset.

---

## 5. What does that actually mean?

This experiment proved that the specification can describe more than individual tables.

It can describe how datasets are connected.

Before 021-B:

```text
Specification

    ↓

CUSTOMER dataset

    +

PRODUCT dataset
```

The datasets were independent.

After 021-B:

```text
Specification
       |
       +----------------+
       |                |
       v                v
   CUSTOMER          PRODUCT
       |                |
       | CUSTOMER_ID    | CUSTOMER_ID
       +----------------+
              1:N
```

The generated datasets now form a relational model.

---

## 6. Why is this important?

This is an important step toward the actual FORGE idea.

A domain owner should eventually be able to describe:

```text
I have these entities.

I have these fields.

These entities are related.

This field references that field.

This relationship is one-to-many.

This relationship is required.
```

They should not need to write Python explaining how to generate the relationship.

The runtime should interpret the model.

The architectural direction is therefore:

```text
Domain Owner
     |
     | Declarative model
     v
FORGE Specification
     |
     v
Generic FORGE Runtime
     |
     v
Relational Dataset
```

---

## 7. What did we learn?

The most important learning is:

> **A field does not always need its own generation logic. Its value can be supplied by a relationship declared elsewhere in the model.**

This gives us an important distinction inside FORGE:

```text
Independent field
        |
        +--> Generate directly


Relationship-managed field
        |
        +--> Resolve from related entity
```

This distinction is fundamental because otherwise the generator would try to independently generate a foreign-key field and could easily create invalid references.

021-B also demonstrated that relationship handling can remain generic.

The Python runtime does not contain logic such as:

```python
if entity == "CUSTOMER":
```

or:

```python
if field == "CUSTOMER_ID":
```

Instead, it reads:

```text
parent_entity
parent_field
child_entity
child_field
cardinality
required
```

from the specification.

---

## 8. What has NOT been proven yet?

021-B does **not** prove that FORGE can handle every type of relationship.

Specifically, we have not yet proven:

* Many-to-many relationships
* Associative entities
* Optional relationship generation at scale
* Multiple levels of relationships
* Complex dependency graphs
* Relationship cycles
* Cross-entity derived fields
* Relationship-aware statistical behavior
* Large datasets
* Complex relational constraints
* Real-world domain models

Those should be tested separately rather than making 021-B responsible for everything.

---

## 9. Architectural outcome

### Before 021-B

021-A established:

> **FORGE can convert a declarative model into independent entity datasets.**

### After 021-B

We have experimentally validated:

> **FORGE can interpret a declaratively defined parent-child relationship, generate entities in the required order, resolve relationship-managed fields, and produce datasets with valid referential integrity.**

The important architectural progression is:

```text
021-A

Declarative Model
       ↓
Independent Datasets
```

becomes:

```text
021-B

Declarative Relational Model
       ↓
Dependency-aware Generation
       ↓
Related Datasets
       ↓
Referential Integrity
```

---

## 10. Resulting FORGE capability

> **FORGE can generate a relational dataset from a declarative model without embedding knowledge of the domain into the generation code.**

The model, rather than the Python implementation, defines how the generated datasets relate to each other.

---

## 11. Evidence

**Experiment:** `021-B`

**Result:** `PASS`

**Entities:** `2`

**Relationships:** `1`

**Relationship:** `CUSTOMER.CUSTOMER_ID → PRODUCT.CUSTOMER_ID`

**Cardinality:** `1:N`

**Relationship-managed fields:** `1`

**Total records:** `150`

**Seed:** `42`

**Scenario:** `NORMAL`

**Generation order:** `CUSTOMER → PRODUCT`

**Referential integrity:** `PASS`

**Reproducibility:** `PASS`

**Seed sensitivity:** `PASS`

**Entity-order independence:** `PASS`

**Dataset format:** `CSV`

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
output/relational_generation_results.json
```

---

## 12. The one-line takeaway

> **021-B proved that FORGE can move from generating independent tables to generating connected relational datasets using relationships defined entirely in the declarative specification.**
