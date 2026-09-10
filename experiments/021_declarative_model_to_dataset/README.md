# Experiment 021: Declarative Model to Dataset

**Status:** Planned

**Experiment Type:** Foundational / Structural / Validation

**FORGE Area:** Declarative Model Execution and Synthetic Dataset Generation

**Objective:** Determine whether a domain-neutral declarative model can be transformed into a valid synthetic dataset without domain-specific generation code.

---

## 1. Research Question

Can FORGE take a declarative specification describing entities, fields, relationships, constraints, dependencies, statistical behaviors, and scenarios, and transform that specification into an actual synthetic dataset?

The experiment family will progressively increase the complexity of the declarative model while keeping the generation engine domain-independent.

---

## 2. Hypothesis

A sufficiently expressive declarative specification can serve as the source of truth for synthetic data generation.

If the specification describes:

- Entities
- Fields
- Relationships
- Constraints
- Dependencies
- Statistical behaviors
- Conditional rules
- Derived values
- Scenarios

then FORGE should be able to determine a valid generation plan and produce a dataset that conforms to the declared model.

The hypothesis assumes that the domain owner describes the desired data model and its expected behavior, while FORGE determines how that model is executed.

The hypothesis does not assume that FORGE understands the business domain automatically.

The hypothesis does not assume that FORGE must reproduce an existing real-world dataset.

The hypothesis does not assume that generation logic must be written specifically for each domain.

The hypothesis will be rejected if:

- The declarative model cannot be translated into an executable generation plan.
- Domain-specific generation code is required for each model.
- The generated dataset violates declared structural or behavioral requirements.
- Increasing model complexity requires changes to the generation engine rather than changes to the declarative specification.
- Invalid or contradictory specifications cannot be detected safely.
- The same generation machinery cannot operate across different domain-neutral relational models.

---

## 3. Scope

This experiment family will validate the transition from a declarative relational model to an actual synthetic dataset.

The experiments will progressively combine the capabilities established during Experiment 020.

### Included

- Declarative model to dataset generation
- Multiple entities and fields
- Entity relationships and cardinality
- Identity and referential integrity
- Field and cross-field constraints
- Dependency-driven generation
- Derived and conditional values
- Statistical behavior and relationships
- Scenario-driven generation
- Population scaling
- Model evolution
- Domain-neutral execution
- Independent dataset validation
- Invalid and contradictory specification handling
- Reproducibility and deterministic behavior

### Excluded

- Automatic discovery of domain semantics from real datasets
- Automatic reverse engineering of an existing database
- Domain-specific business ontology creation
- LLM-based specification authoring
- Automatic inference of the complete declarative model from natural language
- Production-scale deployment and operational infrastructure

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The initial experiment will use a deliberately small and domain-neutral relational model.

The purpose is to validate the fundamental transition:

    Declarative Specification
             ↓
       Model Validation
             ↓
       Generation Planning
             ↓
          Generation
             ↓
           Dataset
             ↓
       Independent Validation

The initial model should remain intentionally simple. Complexity will be introduced progressively in subsequent experiments.

### Entity

`CUSTOMER`

### Fields

| Field | Type | Semantic / Behavior |
|---|---|---|
| CUSTOMER_ID | identifier | Unique sequential identity |
| CUSTOMER_SCORE | float | Generated numerical value within declared bounds |
| CUSTOMER_TYPE | categorical | Generated from declared categorical values |
| IS_ACTIVE | boolean | Generated according to declared population behavior |

A second independent entity may be introduced where required to validate that the generator operates across multiple entities.

### Entity

`PRODUCT`

### Fields

| Field | Type | Semantic / Behavior |
|---|---|---|
| PRODUCT_ID | identifier | Unique sequential identity |
| PRODUCT_PRICE | decimal | Generated within declared bounds |
| PRODUCT_TYPE | categorical | Generated from declared categorical values |

The initial experiment intentionally avoids complex relationships, cross-entity constraints, and advanced statistical relationships.

Those capabilities will be introduced progressively.

---

## 5. Experiment Configuration

The experiment will consume a declarative specification rather than domain-specific generation code.

The specification defines the model that FORGE must execute.

Example:

```json
{
  "entities": [
    {
      "name": "CUSTOMER",
      "fields": [
        {
          "name": "CUSTOMER_ID",
          "type": "IDENTIFIER",
          "strategy": "SEQUENTIAL"
        },
        {
          "name": "CUSTOMER_SCORE",
          "type": "FLOAT",
          "strategy": "RANDOM",
          "distribution": "UNIFORM",
          "parameters": {
            "minimum": 0,
            "maximum": 100
          }
        },
        {
          "name": "CUSTOMER_TYPE",
          "type": "CATEGORICAL",
          "strategy": "RANDOM",
          "distribution": "CATEGORICAL",
          "parameters": {
            "values": [
              "STANDARD",
              "PREMIUM"
            ]
          }
        },
        {
          "name": "IS_ACTIVE",
          "type": "BOOLEAN",
          "strategy": "RANDOM"
        }
      ]
    }
  ],
  "relationships": [],
  "constraints": [],
  "dependencies": [],
  "statistical_behavior": [],
  "scenarios": []
}
````

The experiment must not contain entity-specific generation functions.

The generation runtime must derive its behavior from the specification.

---

## 6. Generation Process

The expected execution flow is:

```text
Declarative Specification
          ↓
Specification Validation
          ↓
Capability Assessment
          ↓
Requirement Extraction
          ↓
Generation Planning
          ↓
Dataset Generation
          ↓
Independent Validation
```

The generated dataset should be an explicit experiment artifact.

---

## 7. Validation

The generated dataset will be independently evaluated against the declarative specification.

Validation will include:

* Entity structure
* Field presence
* Field type
* Population count
* Identity uniqueness
* Declared field behavior
* Declared bounds
* Reproducibility
* Seed sensitivity
* Field-order independence
* Configuration safety
* Absence of hidden fallback
* Absence of post-generation repair

Where later experiments introduce additional capabilities, validation will be extended accordingly.

---

## 8. Success Criteria

The experiment is successful when:

1. FORGE consumes the declarative specification successfully.
2. FORGE produces an actual dataset from the specification.
3. The generated dataset conforms to the declared model.
4. No domain-specific generation code is required.
5. The same generation mechanism can operate on structurally different specifications.
6. Generation is reproducible for the same specification and seed.
7. Changing the seed produces meaningfully different generated populations where randomness is declared.
8. Invalid configurations are rejected rather than silently corrected.
9. The generated dataset can be independently validated against the specification.

---

## 9. Experiment Progression

The 021 experiment family will progressively increase the complexity of the model.

### 021-A - Basic Declarative Model to Dataset

Validate the fundamental specification-to-dataset transition.

### 021-B - Multi-Entity Relational Dataset

Introduce multiple related entities and validate relational integrity.

### 021-C - Behavioral Dataset Generation

Introduce constraints, dependencies, derived values, conditional rules, and statistical behavior.

### 021-D - Integrated Declarative Dataset

Combine structural and behavioral requirements within a single model.

### 021-E - Scenario-Driven Dataset

Generate different populations from the same base model using declarative scenarios.

### 021-F - Population Scaling

Generate different population sizes from the same declarative model.

### 021-G - Model Evolution

Change the declarative model without changing the generation engine.

### 021-H - Domain-Neutral Model Execution

Validate that structurally different relational models can use the same FORGE runtime.

### 021-I - Adversarial Model Validation

Introduce contradictory, impossible, ambiguous, and unsupported specifications and verify safe rejection.

### 021-J - Capstone Declarative Model to Dataset

Validate the complete model-to-dataset pipeline using a sufficiently complex domain-neutral specification.

---

## 10. Expected Evidence

Each experiment should produce tangible evidence wherever generation is performed.

Typical outputs include:

```text
output/
├── dataset.json
├── dataset.csv
├── generation_manifest.json
└── <experiment>_results.json
```

The primary evidence for Experiment 021 is therefore not only test results.

It is:

```text
Declarative Model
       ↓
   Actual Dataset
       ↓
Independent Validation
```

The generated dataset should demonstrate that the declarative model is executable.

---

## 11. Architectural Principle

Experiment 021 is built around the following principle:

> The model describes the data reality. FORGE executes the model.

The declarative specification should describe:

```text
Entities
Fields
Relationships
Constraints
Dependencies
Statistical Behaviors
Conditional Rules
Derived Values
Scenarios
```

FORGE should determine:

```text
Generation Order
Generation Strategy
Randomness
Feasible Regions
Relationship Resolution
Statistical Generation
Validation
Provenance
```

The separation between the model and the generation mechanism is a fundamental architectural requirement.

---

## 12. Expected Outcome

A successful Experiment 021 should establish that FORGE has moved beyond individual generation capabilities and can execute a declarative model as a complete synthetic data generation system.

The desired outcome is:

```text
Declarative Model
        ↓
      FORGE
        ↓
Generation Plan
        ↓
Synthetic Dataset
        ↓
Independent Validation
```

This establishes the foundation for FORGE as a domain-independent, model-driven synthetic data generation platform.
