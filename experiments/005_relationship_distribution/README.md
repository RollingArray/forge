# Experiment 005: Relationship Distribution

**Status:** Planned  
**Experiment Type:** Statistical / Relational  
**FORGE Area:** Relationships / Generation  
**Objective:** Determine whether FORGE can control the statistical distribution of child records across parent records while maintaining referential integrity.

---

## 1. Research Question

Can synthetic data maintain valid parent-child relationships while also controlling how child records are distributed across parent entities?

---

## 2. Hypothesis

A synthetic dataset can maintain referential integrity while applying an explicit distribution strategy to the allocation of child records.

The generator should be able to distinguish between:

- **Relationship validity**: every child reference points to a valid parent.
- **Relationship distribution**: the number of children associated with each parent follows a declared statistical intent.

The experiment will initially evaluate:

- Uniform relationship distribution
- Weighted relationship distribution
- Parent records receiving zero or multiple child records
- Preservation of the declared `1:N` cardinality
- Referential integrity

The purpose is to determine whether **relationship allocation itself can be treated as a configurable generation characteristic**, rather than being left to random assignment.

---

## 3. Scope

This experiment builds directly on the capabilities established in Experiments 001 through 004.

It combines:

- Metadata-driven generation from Experiment 001
- Field constraints from Experiment 002
- Statistical distributions from Experiment 003
- Referential relationships from Experiment 004

### Included

- Entity definition
- Field definition
- Field constraints
- Categorical distributions
- Numeric distributions
- Parent-child relationships
- `1:N` cardinality
- Uniform child allocation
- Weighted child allocation
- Referential integrity validation
- Relationship distribution validation
- Configurable record volume
- Deterministic random seed
- Generated entity outputs
- Relationship statistics output

### Excluded

- Real production data
- Machine Learning
- Deep Learning
- Large Language Models
- Distribution inference from real data
- Cross-field correlation
- Conditional relationships
- Complex business rules
- Temporal relationships
- Many-to-many relationships
- Domain-specific SAP, PLM, MES or ERP logic
- Advanced statistical similarity metrics

These capabilities will be explored in later experiments.

---

## 4. Initial Entity Model

The experiment will use the same generic entities established in Experiment 004.

### CUSTOMER

| Field | Type | Semantic / Behavior |
|---|---|---|
| CUSTOMER_ID | identifier | Unique parent identifier |
| COUNTRY | categorical | Weighted categorical distribution |

### ORDER

| Field | Type | Semantic / Behavior |
|---|---|---|
| ORDER_ID | identifier | Unique child identifier |
| AMOUNT | integer | Bounded statistical distribution |
| CUSTOMER_ID | reference | References `CUSTOMER.CUSTOMER_ID` |

The entities remain intentionally domain-neutral.

---

## 5. Relationship

The experiment will define the following relationship:

```text
CUSTOMER.CUSTOMER_ID
        |
        | 1:N
        |
ORDER.CUSTOMER_ID