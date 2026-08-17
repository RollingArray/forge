# Experiment 004: Relationship-Aware Generation

**Status:** Planned  
**Experiment Type:** Relationship  
**FORGE Area:** Relationships / Generation  
**Objective:** Determine whether synthetic data can maintain valid relationships between entities using relationship metadata without requiring real production data.

---

## 1. Research Question

Can a synthetic data generator create multiple related entities while
maintaining referential integrity and declared relationship cardinality
using only metadata?

---

## 2. Hypothesis

A synthetic dataset can maintain structurally valid relationships when
relationships are explicitly defined as part of the generation
specification.

The generator should be able to:

- Identify parent and child entities.
- Generate parent records before dependent records.
- Reuse generated identifiers across related entities.
- Maintain referential integrity.
- Support one-to-many relationships.
- Control the number of child records associated with a parent.
- Prevent references to non-existent parent records.

The experiment will determine whether **relationships can be treated as
generation instructions rather than being inferred from generated data**.

The experiment does not attempt to model complex business relationships
at this stage.

---

## 3. Scope

This experiment will generate a small synthetic dataset containing
multiple related entities.

The experiment will build on the metadata, field constraint and
distribution capabilities explored in Experiments 001, 002 and 003.

### Included

- Multiple entity definitions
- Primary identifiers
- Foreign identifiers
- Parent-child relationships
- One-to-many relationships
- Referential integrity
- Parent-first generation
- Reuse of generated identifiers
- Configurable parent volume
- Configurable child volume
- Deterministic generation
- Relationship validation
- Generation output

### Excluded

- Real production data
- Machine Learning
- Deep Learning
- Large Language Models
- Relationship inference from real data
- Many-to-many relationships
- Complex business rules
- Conditional relationships
- Temporal relationships
- Domain-specific SAP, PLM, MES or ERP logic
- Advanced graph generation

These capabilities may be explored in later experiments.

---

## 4. Initial Entities

The experiment will use two generic entities:

```text
CUSTOMER
    │
    │  1:N
    ▼
ORDER