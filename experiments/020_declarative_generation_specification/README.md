# Experiment 020: Declarative Generation Specification

**Status:** In Progress  
**Experiment Type:** Foundational / Structural / Relationship / Rule / Statistical / Validation  
**FORGE Area:** Controlled Vocabulary / Declarative Specification / Generation Planning / Generic Generation Engine  
**Objective:** Determine whether the complete FORGE Controlled Vocabulary v1 can represent and drive end-to-end synthetic generation of a realistic relational dataset through a domain-neutral declarative specification without embedding business-specific generation logic in the generation engine.

---

## 1. Research Question

Can a sufficiently expressive controlled vocabulary provide a generic
declarative language for synthetic data generation?

More specifically:

> Can FORGE describe and generate a complete relational dataset by
> changing only the declarative specification while keeping the
> generation engine unchanged?

The experiment investigates whether generation intent can be expressed
through one coherent specification covering:

- data types
- semantic types
- generation strategies
- probability distributions
- identity
- composite keys
- relationships
- dependencies
- conditional rules
- derived values
- population
- nullability
- scenarios
- temporal behavior
- statistical behavior
- generation controls
- validation
- provenance

The experiment is deliberately designed around a small but realistic
relational system rather than a single isolated entity.

The objective is not to prove that FORGE can generate one particular
dataset.

The objective is to determine whether:

> **FORGE can express generation intent generically, derive an execution
> plan from that intent, and generate a complete relational dataset
> without embedding business-specific generation logic in the engine.**

---

# 2. Hypothesis

A complete controlled vocabulary combined with a structured declarative
specification can express a broad range of general-purpose synthetic data
generation requirements.

The same generic generation engine should be capable of generating the
complete relational model by interpreting the specification.

A materially different generation requirement should therefore be
achievable by changing the specification rather than changing the
generator implementation.

### The generator is expected to

- interpret the FORGE specification generically
- resolve vocabulary elements through a controlled registry
- validate the specification before generation
- identify entity and field dependencies
- derive a generation order
- construct an executable generation plan
- execute generation strategies
- execute distributions
- maintain identity
- maintain referential integrity
- execute declarative rules
- generate derived values
- support composite keys
- support parent and child dependencies
- support optional relationships
- support scenarios
- support statistical requirements
- produce reproducible output
- produce validation evidence
- produce provenance

### Assumptions

The experiment assumes that:

- generation intent can be represented declaratively
- generic primitives can be composed into more complex behavior
- entity relationships can be represented independently of domain-specific
  generation code
- dependencies can be represented explicitly
- generation order can be derived from dependencies
- validation can be separated from generation
- provenance can be generated from execution context

### Intentionally not assumed

The experiment does not assume that:

- every possible business rule is already known
- every possible business domain can be fully represented by this one
  vocabulary
- every possible statistical distribution is required
- a language model can correctly create the specification
- syntactically valid specifications are necessarily semantically valid
- a generated dataset is statistically representative merely because
  individual fields are valid
- the six-entity model represents a universal business domain

### Hypothesis rejection

The hypothesis will be rejected if:

- materially different generation requirements require generator
  source-code changes
- business-specific logic must be embedded in the generator
- dependencies cannot be represented generically
- the generation order must be manually hard-coded
- relationships require entity-specific generation logic
- composite identities cannot be represented generically
- rules cannot be composed
- invalid specifications cannot be detected before generation
- unsupported vocabulary is silently accepted
- reproducibility cannot be demonstrated

---

# 3. Scope

This experiment establishes the FORGE Controlled Vocabulary v1 and tests
whether the vocabulary can drive end-to-end generation of a compact but
realistic relational system.

Experiments 001-019 established individual capabilities.

Experiment 020 tests whether those capabilities can be composed through
one declarative specification and one generic generation engine.

### Included

- Complete FORGE Controlled Vocabulary v1
- Machine-readable vocabulary registry
- Declarative specification model
- Specification semantic validation
- Entity definitions
- Field definitions
- Primitive and semantic types
- Generation strategies
- Probability distributions
- Primary and foreign keys
- Composite keys
- Natural and surrogate identities
- 1:1 relationships
- 1:N relationships
- 0:N relationships
- N:M relationships through an associative entity
- Field dependencies
- Parent dependencies
- Child dependencies
- Conditional dependencies
- Sequential dependencies
- Temporal dependencies
- Statistical dependencies
- Declarative rules
- Derived values
- Population and nullability
- Scenarios
- Statistical behavior
- Generation controls
- Dependency analysis
- Generation planning
- Generic generation
- Unified validation
- Provenance and evidence
- Reproducibility
- Specification substitution
- Domain-neutrality
- Invalid specification handling

### Excluded

- Graphical user interface
- Natural-language interpretation
- LLM integration
- Learning business rules from sample data
- Training-based synthetic generation
- Production REST APIs
- Distributed generation
- Enterprise deployment
- Production-scale optimization

These capabilities are intentionally separated from the declarative
generation foundation.

---

# 4. Initial Dataset / Entity

The experiment uses a deliberately compact but structurally rich
relational model.

The model is not intended to represent a particular real-world business
system.

Its purpose is to provide enough relational complexity to test the
composition of the FORGE vocabulary.

The model contains six entities:

```text
CUSTOMER
    |
    +---- CUSTOMER_PROFILE
    |
    +---- ORDER
             |
             +---- ORDER_ITEM ---- PRODUCT
             |
             +---- SHIPMENT
````

This model allows the experiment to exercise:

* 1:1
* 1:N
* 0:N
* N:M
* parent/child relationships
* optional relationships
* foreign keys
* composite keys
* natural keys
* surrogate keys
* field dependencies
* parent dependencies
* temporal dependencies
* derived values

The six entities are intentionally sufficient for the experiment.
Additional entities should not be added merely to increase dataset size.

---

## 4.1 Entity: CUSTOMER

`CUSTOMER` is the root entity.

| Field          | Type        | Semantic / Behavior                               |
| -------------- | ----------- | ------------------------------------------------- |
| CUSTOMER_ID    | IDENTIFIER  | Primary key, surrogate key, sequential identifier |
| CUSTOMER_CODE  | CODE        | Unique business-facing code                       |
| CUSTOMER_TYPE  | ENUM        | STANDARD / PREMIUM                                |
| COUNTRY        | CATEGORICAL | Weighted categorical generation                   |
| CREDIT_LIMIT   | CURRENCY    | Conditional / parent-independent generation       |
| CUSTOMER_SCORE | FLOAT       | Statistical numeric generation                    |
| IS_ACTIVE      | BOOLEAN     | Boolean generation                                |
| EMAIL          | STRING      | Controlled population and nullability             |
| CREATED_DATE   | DATE        | Date generation                                   |

---

## 4.2 Entity: CUSTOMER_PROFILE

`CUSTOMER_PROFILE` provides a 1:1 dependent entity.

| Field                | Type        | Semantic / Behavior             |
| -------------------- | ----------- | ------------------------------- |
| CUSTOMER_ID          | FOREIGN_KEY | Reference to CUSTOMER           |
| PROFILE_STATUS       | ENUM        | Profile state                   |
| PHONE_CODE           | CODE        | Generated code                  |
| PREFERRED_LANGUAGE   | CATEGORICAL | Weighted categorical generation |
| PROFILE_CREATED_DATE | DATE        | Parent-dependent date           |

### Identity

```text
PRIMARY KEY = CUSTOMER_ID
FOREIGN KEY = CUSTOMER.CUSTOMER_ID
```

Relationship:

```text
CUSTOMER 1:1 CUSTOMER_PROFILE
```

---

## 4.3 Entity: PRODUCT

`PRODUCT` represents a reference/master entity.

| Field           | Type       | Semantic / Behavior                    |
| --------------- | ---------- | -------------------------------------- |
| PRODUCT_ID      | IDENTIFIER | Surrogate primary key                  |
| PRODUCT_CODE    | CODE       | Natural business identifier            |
| PRODUCT_VERSION | INTEGER    | Part of composite natural key          |
| PRODUCT_TYPE    | ENUM       | PRODUCT / SERVICE                      |
| UNIT_PRICE      | CURRENCY   | Distribution-driven numeric generation |
| IS_ACTIVE       | BOOLEAN    | Boolean generation                     |

### Identity

```text
PRIMARY KEY = PRODUCT_ID

NATURAL KEY =
    (PRODUCT_CODE, PRODUCT_VERSION)
```

This entity allows the experiment to distinguish between:

* surrogate identity
* natural identity
* composite identity
* uniqueness

---

## 4.4 Entity: ORDER

`ORDER` is the transactional child of CUSTOMER.

| Field        | Type        | Semantic / Behavior                     |
| ------------ | ----------- | --------------------------------------- |
| ORDER_ID     | IDENTIFIER  | Primary key, sequential identifier      |
| CUSTOMER_ID  | FOREIGN_KEY | Required reference to CUSTOMER          |
| ORDER_NUMBER | CODE        | Unique business identifier              |
| ORDER_DATE   | DATE        | Temporal generation                     |
| ORDER_TIME   | TIME        | Time generation                         |
| MIN_AMOUNT   | CURRENCY    | Numeric generation                      |
| MAX_AMOUNT   | CURRENCY    | Numeric generation                      |
| AMOUNT       | CURRENCY    | Parent/conditional dependent generation |
| DISCOUNT     | PERCENTAGE  | Numeric generation with constraints     |
| QUANTITY     | INTEGER     | Numeric generation                      |
| STATUS       | ENUM        | Order lifecycle state                   |
| IS_PRIORITY  | BOOLEAN     | Conditional generation                  |
| SUBTOTAL     | CURRENCY    | Derived from ORDER_ITEM values          |
| NET_AMOUNT   | CURRENCY    | Derived from SUBTOTAL and DISCOUNT      |

### Identity

```text
PRIMARY KEY = ORDER_ID
FOREIGN KEY = CUSTOMER.CUSTOMER_ID
```

Relationship:

```text
CUSTOMER 1:N ORDER
```

---

## 4.5 Entity: ORDER_ITEM

`ORDER_ITEM` provides the associative structure between ORDER and PRODUCT.

| Field       | Type        | Semantic / Behavior                |
| ----------- | ----------- | ---------------------------------- |
| ORDER_ID    | FOREIGN_KEY | Reference to ORDER                 |
| LINE_NUMBER | INTEGER     | Sequential within ORDER            |
| PRODUCT_ID  | FOREIGN_KEY | Reference to PRODUCT               |
| QUANTITY    | INTEGER     | Numeric generation                 |
| UNIT_PRICE  | CURRENCY    | Product-dependent value            |
| LINE_AMOUNT | CURRENCY    | Derived from QUANTITY × UNIT_PRICE |

### Identity

```text
PRIMARY KEY =
    (ORDER_ID, LINE_NUMBER)
```

Foreign keys:

```text
ORDER_ID   -> ORDER.ORDER_ID
PRODUCT_ID -> PRODUCT.PRODUCT_ID
```

This provides the associative structure:

```text
ORDER
   |
   N
   |
ORDER_ITEM
   |
   N
   |
PRODUCT
```

Therefore:

```text
ORDER N:M PRODUCT
```

is represented through `ORDER_ITEM`.

This is important because the experiment does not merely declare an
N:M vocabulary value. It tests whether the generic generation model can
materialize an N:M relationship through an associative entity.

---

## 4.6 Entity: SHIPMENT

`SHIPMENT` provides an optional downstream relationship.

| Field         | Type        | Semantic / Behavior                  |
| ------------- | ----------- | ------------------------------------ |
| SHIPMENT_ID   | IDENTIFIER  | Primary key                          |
| ORDER_ID      | FOREIGN_KEY | Reference to ORDER                   |
| SHIPMENT_DATE | DATE        | Temporal dependency on ORDER_DATE    |
| DELIVERY_DATE | DATE        | Temporal dependency on SHIPMENT_DATE |
| CARRIER_CODE  | CODE        | Categorical/code generation          |
| SHIPPING_COST | CURRENCY    | Distribution-driven generation       |
| STATUS        | ENUM        | Shipment state                       |

Relationship:

```text
ORDER 0:N SHIPMENT
```

An order may therefore have:

* zero shipments
* one shipment
* multiple shipments

This provides a genuine optional relationship for the experiment.

---

# 5. Experiment Configuration

The experiment is driven entirely by a declarative FORGE specification.

The specification describes generation intent rather than executable
implementation logic.

Conceptually:

```json
{
  "version": "1.0",

  "controls": {
    "seed": 42,
    "deterministic": true,
    "record_order": "stable"
  },

  "entities": [
    {
      "name": "CUSTOMER",
      "population": 100,
      "fields": []
    },
    {
      "name": "CUSTOMER_PROFILE",
      "population": 100,
      "fields": []
    },
    {
      "name": "PRODUCT",
      "population": 50,
      "fields": []
    },
    {
      "name": "ORDER",
      "population": 1000,
      "fields": []
    },
    {
      "name": "ORDER_ITEM",
      "population": 2500,
      "fields": []
    },
    {
      "name": "SHIPMENT",
      "population": 600,
      "fields": []
    }
  ],

  "relationships": [],

  "rules": [],

  "scenarios": []
}
```

The actual specification is stored in:

```text
experiments/020_declarative_generation_specification/specification.json
```

The generation engine must not contain business-specific configuration
outside the specification.

---

# 6. FORGE Controlled Vocabulary v1

This experiment establishes the target FORGE Controlled Vocabulary v1.

The vocabulary defines the controlled language through which FORGE
expresses generation intent.

It is organized into twelve domains.

---

## 6.1 Type System

### Primitive

* `INTEGER`
* `DECIMAL`
* `FLOAT`
* `STRING`
* `BOOLEAN`
* `DATE`
* `DATETIME`
* `TIME`

### Semantic

* `CATEGORICAL`
* `ENUM`
* `IDENTIFIER`
* `CODE`
* `PERCENTAGE`
* `CURRENCY`

Semantic types may impose additional generation and validation semantics
over primitive representations.

For example:

```text
CURRENCY
    underlying representation -> DECIMAL

PERCENTAGE
    underlying representation -> DECIMAL

IDENTIFIER
    underlying representation -> STRING
```

---

# 7. Generation Strategies

* `CONSTANT`
* `SEQUENTIAL`
* `RANDOM`
* `SAMPLE`
* `REFERENCE`
* `LOOKUP`
* `CONDITIONAL`
* `DERIVED`
* `FORMULA`
* `TRANSFORM`
* `COPY`
* `NULL`

Generation strategy describes how a value is produced.

Distribution describes the statistical behavior of a generated value.

These are deliberately separate concepts.

For example:

```text
RANDOM
    +
UNIFORM
```

is different from:

```text
CONSTANT
```

and:

```text
CONDITIONAL
    +
RANDOM
    +
NORMAL
```

---

# 8. Distributions

* `UNIFORM`
* `NORMAL`
* `LOGNORMAL`
* `EXPONENTIAL`
* `GAMMA`
* `BETA`
* `WEIBULL`
* `TRIANGULAR`
* `DISCRETE_UNIFORM`
* `BINOMIAL`
* `POISSON`
* `CATEGORICAL`
* `EMPIRICAL`
* `TRUNCATED`
* `MIXTURE`

Distribution implementations must remain domain-neutral.

A distribution implementation should not know whether the generated
field is `ORDER_AMOUNT`, `UNIT_PRICE`, or `CUSTOMER_SCORE`.

---

# 9. Identity

* `PRIMARY_KEY`
* `FOREIGN_KEY`
* `COMPOSITE_KEY`
* `NATURAL_KEY`
* `SURROGATE_KEY`
* `UNIQUE`
* `STABLE`
* `SEQUENTIAL_ID`
* `UUID`
* `COMPOSITE_ID`

The experiment must demonstrate that identity semantics can be declared
independently from the mechanism used to produce the underlying values.

---

# 10. Relationships

### Cardinality

* `1:1`
* `0:1`
* `1:N`
* `0:N`
* `N:M`

### Relationship semantics

* `PARENT`
* `CHILD`
* `ASSOCIATIVE`
* `REQUIRED`
* `OPTIONAL`
* `DEPENDENT`

The experiment specifically exercises:

```text
CUSTOMER          1:1  CUSTOMER_PROFILE

CUSTOMER          1:N  ORDER

ORDER             N:M  PRODUCT
                       through ORDER_ITEM

ORDER             0:N  SHIPMENT
```

---

# 11. Dependencies

* `FIELD_DEPENDENCY`
* `CONDITIONAL_DEPENDENCY`
* `PARENT_DEPENDENCY`
* `CHILD_DEPENDENCY`
* `SEQUENTIAL_DEPENDENCY`
* `TEMPORAL_DEPENDENCY`
* `STATISTICAL_DEPENDENCY`

Dependencies must participate in generation planning.

Generation order must be derived from declared dependencies rather than
being manually encoded.

---

# 12. Rule Language

The rule language provides generic operators for representing constraints
and derived behavior.

## Comparison

* `EQUALS`
* `NOT_EQUALS`
* `GREATER_THAN`
* `LESS_THAN`
* `GREATER_OR_EQUAL`
* `LESS_OR_EQUAL`
* `BETWEEN`

## Membership

* `IN`
* `NOT_IN`

## Null

* `IS_NULL`
* `IS_NOT_NULL`

## Logic

* `AND`
* `OR`
* `NOT`
* `XOR`
* `IMPLIES`

## Conditional

* `IF`
* `THEN`
* `ELSE`

## Arithmetic

* `ADD`
* `SUBTRACT`
* `MULTIPLY`
* `DIVIDE`
* `MODULO`
* `ABS`
* `MIN`
* `MAX`
* `ROUND`
* `FLOOR`
* `CEILING`

## String

* `CONCAT`
* `LENGTH`
* `CONTAINS`
* `STARTS_WITH`
* `ENDS_WITH`
* `MATCH`
* `UPPER`
* `LOWER`
* `TRIM`
* `REPLACE`

## Date / Time

* `DATE_ADD`
* `DATE_SUBTRACT`
* `DATE_DIFF`

## Data Access

* `REFERENCE`
* `LOOKUP`
* `SAMPLE`
* `DERIVE`

Rules must be represented as structured expressions.

Example:

```text
MIN_AMOUNT <= MAX_AMOUNT
```

is represented conceptually as:

```text
LESS_OR_EQUAL(
    FIELD("MIN_AMOUNT"),
    FIELD("MAX_AMOUNT")
)
```

The expression must be interpreted by a generic rule engine.

---

# 13. Population / Nullability

* `POPULATION_RATE`
* `POPULATION_COUNT`
* `ALWAYS`
* `NEVER`
* `OPTIONAL`
* `NULLABLE`
* `NOT_NULL`

Population and nullability are generation semantics.

They must not be implemented as arbitrary post-processing steps.

---

# 14. Scenarios

* `SCENARIO`
* `SCENARIO_PARAMETER`
* `SCENARIO_OVERRIDE`
* `SCENARIO_CONSTRAINT`
* `SCENARIO_DISTRIBUTION`

Example scenarios:

```text
NORMAL
HIGH_VALUE
MISSING_DATA
PEAK_PERIOD
```

Scenario changes may affect:

* population
* distribution
* categorical weights
* nullability
* constraints
* generation parameters

Scenario behavior must remain declarative.

---

# 15. Correlation / Statistical Behavior

* `CORRELATION`
* `TARGET_CORRELATION`
* `POSITIVE`
* `NEGATIVE`
* `PEARSON`
* `SPEARMAN`

The specification represents requested statistical behavior.

The generated dataset provides observed behavior.

Validation determines whether the observed behavior satisfies the
declared requirement.

---

# 16. Generation Control

* `SEED`
* `RANDOM_STREAM`
* `RANDOM_STATE`
* `DETERMINISTIC`
* `RECORD_COUNT`
* `RECORD_ORDER`
* `PRIORITY`

These controls provide deterministic and reproducible execution.

---

# 17. Validation / Evidence

* `VALIDATION`
* `PROVENANCE`
* `REPRODUCIBILITY`
* `EVIDENCE_ID`
* `STRUCTURAL_VALID`
* `CONSTRAINT_VALID`
* `RELATIONSHIP_VALID`
* `DEPENDENCY_VALID`
* `DISTRIBUTION_VALID`
* `STATISTICAL_VALID`
* `PROVENANCE_VALID`

Validation and evidence describe how FORGE demonstrates that generated
output conforms to the declared specification.

---

# 18. Vocabulary Registry

The vocabulary must be implemented through a centralized machine-readable
registry.

Each vocabulary element should provide metadata including:

* identifier
* category
* semantic meaning
* supported data types
* required parameters
* optional parameters
* operand requirements
* implementation status
* validation status

The registry becomes the controlled boundary between the declarative
specification and runtime implementation.

Vocabulary strings must not be scattered as arbitrary literals throughout
the generator.

---

# 19. Vocabulary Lifecycle

Every vocabulary item should have an explicit implementation state.

### REGISTERED

The item is part of the FORGE vocabulary.

### IMPLEMENTED

A runtime implementation exists.

### VALIDATED

The implementation has been exercised and validated.

This distinction prevents a dangerous behavior where a vocabulary item is
accepted but silently mapped to an unrelated implementation.

Example:

```text
WEIBULL

Vocabulary:
    REGISTERED

Runtime:
    IMPLEMENTED

Validation:
    VALIDATED
```

If an item is registered but unavailable:

```text
Vocabulary:
    REGISTERED

Runtime:
    NOT_IMPLEMENTED

Generation:
    BLOCKED
```

---

# 20. Declarative Specification Model

The specification represents what should be generated.

It does not describe how Python, SQL, or another runtime should generate
the data.

Conceptually:

```text
FIELD
 |
 +-- type
 |
 +-- semantic
 |
 +-- generation
 |    |
 |    +-- strategy
 |    +-- distribution
 |    +-- parameters
 |
 +-- identity
 |
 +-- population
 |
 +-- nullability
 |
 +-- dependencies
 |
 +-- rules
```

Valid:

```json
{
  "strategy": "RANDOM",
  "distribution": "UNIFORM",
  "parameters": {
    "min": 100,
    "max": 500
  }
}
```

Invalid:

```python
random.uniform(100, 500)
```

The first expresses declarative intent.

The second embeds implementation.

---

# 21. Specification Validation

Validation must occur before generation.

The validator must detect:

* unknown vocabulary
* unsupported type
* incompatible type/operator combination
* missing field reference
* missing entity reference
* invalid distribution parameters
* invalid identity configuration
* invalid relationship target
* invalid population configuration
* conflicting constraints
* circular dependencies
* invalid scenario overrides
* invalid expression structure

A syntactically valid specification is not necessarily semantically valid.

---

# 22. Generation Architecture

The intended architecture is:

```text
                 FORGE Specification
                         |
                         v
                Vocabulary Resolution
                         |
                         v
                Specification Validation
                         |
                         v
                  Dependency Analysis
                         |
                         v
                  Generation Planning
                         |
                         v
                 Generic Generator
                         |
                         v
                  Synthetic Dataset
                         |
                +--------+--------+
                |                 |
                v                 v
           Validation        Provenance
```

The generator is responsible for execution.

The specification is responsible for intent.

---

# 23. Generation Planning

The specification must be transformed into an explicit generation plan.

For the six-entity model, the plan may resemble:

```text
01  PRODUCT
02  CUSTOMER
03  CUSTOMER_PROFILE
04  ORDER
05  ORDER_ITEM
06  SHIPMENT
```

with field-level dependencies determining the exact execution order.

For example:

```text
CUSTOMER.CUSTOMER_ID
        |
        +--> CUSTOMER_PROFILE.CUSTOMER_ID
        |
        +--> ORDER.CUSTOMER_ID

PRODUCT.PRODUCT_ID
        |
        +--> ORDER_ITEM.PRODUCT_ID

ORDER.ORDER_ID
        |
        +--> ORDER_ITEM.ORDER_ID
        |
        +--> SHIPMENT.ORDER_ID

ORDER.ORDER_DATE
        |
        +--> SHIPMENT.SHIPMENT_DATE
        |
        +--> SHIPMENT.DELIVERY_DATE
```

The exact order must be derived from the specification.

It must not be hard-coded specifically for this model.

---

# 24. End-to-End Dependency Graph

The experiment should produce an inspectable dependency graph.

Conceptually:

```text
                         CUSTOMER
                         /      \
                        /        \
                       v          v
             CUSTOMER_PROFILE    ORDER
                                  |
                                  |
                         +--------+--------+
                         |                 |
                         v                 v
                    ORDER_ITEM         SHIPMENT
                         |
                         |
                         v
                      PRODUCT
```

Field-level dependencies are layered on top:

```text
CUSTOMER_TYPE
      |
      v
CREDIT_LIMIT

CUSTOMER_ID
      |
      v
ORDER.CUSTOMER_ID

ORDER_ID
      |
      v
ORDER_ITEM.ORDER_ID

PRODUCT_ID
      |
      v
ORDER_ITEM.PRODUCT_ID

ORDER_DATE
      |
      v
SHIPMENT_DATE
      |
      v
DELIVERY_DATE
```

This graph is one of the primary artifacts produced by the experiment.

---

# 25. Derived Values

The model deliberately includes derived values.

For example:

```text
ORDER_ITEM.QUANTITY
        *
ORDER_ITEM.UNIT_PRICE
        |
        v
ORDER_ITEM.LINE_AMOUNT
```

Then:

```text
SUM(ORDER_ITEM.LINE_AMOUNT)
        |
        v
ORDER.SUBTOTAL
```

And:

```text
ORDER.SUBTOTAL
       -
ORDER.DISCOUNT
       |
       v
ORDER.NET_AMOUNT
```

The objective is to determine whether these relationships can be
expressed through generic formulas and derivation rules.

No order-specific calculation should be embedded directly into the
generator.

---

# 26. Composite Identity

`ORDER_ITEM` deliberately uses a composite primary key:

```text
PRIMARY KEY =
    (ORDER_ID, LINE_NUMBER)
```

This allows the experiment to test:

* `COMPOSITE_KEY`
* `COMPOSITE_ID`
* `SEQUENTIAL_ID`
* `UNIQUE`
* parent dependency
* child dependency

The experiment should verify that:

* line numbers are unique within an order
* the composite key is globally unique
* the parent ORDER exists
* PRODUCT references are valid

---

# 27. Natural and Surrogate Identity

`PRODUCT` deliberately contains both:

```text
SURROGATE KEY
    PRODUCT_ID

NATURAL KEY
    (PRODUCT_CODE, PRODUCT_VERSION)
```

The experiment should verify that the specification can represent both
identity concepts without confusing their generation semantics.

---

# 28. Temporal Dependencies

The `SHIPMENT` entity provides a realistic temporal dependency.

The specification should express:

```text
SHIPMENT_DATE >= ORDER_DATE

DELIVERY_DATE >= SHIPMENT_DATE
```

The generation model may express this through:

```text
TEMPORAL_DEPENDENCY
DATE_ADD
DATE_DIFF
GREATER_OR_EQUAL
```

The generated data must be validated against the declared temporal rules.

---

# 29. Statistical Dependencies

The experiment should include at least one declarative statistical
relationship.

For example:

```text
CUSTOMER_SCORE
        |
        v
CREDIT_LIMIT
```

or:

```text
QUANTITY
        |
        v
ORDER_ITEM.LINE_AMOUNT
```

Where correlation is explicitly declared, the generated output must be
validated against the requested statistical behavior.

The experiment should distinguish:

```text
DECLARED
    |
    v
TARGET BEHAVIOR
    |
    v
OBSERVED DATA
    |
    v
STATISTICAL VALIDATION
```

---

# 30. Scenario Execution

The relational model should be generated under multiple scenarios.

### NORMAL

Baseline population and distributions.

### HIGH_VALUE

Examples:

* higher CREDIT_LIMIT
* higher ORDER amount
* higher UNIT_PRICE
* increased high-value customer proportion

### MISSING_DATA

Examples:

* lower EMAIL population
* optional profile fields missing
* reduced optional shipment population

### PEAK_PERIOD

Examples:

* increased ORDER population
* increased ORDER_ITEM population
* increased SHIPMENT population
* changed date distribution

The scenarios must be represented through declarative overrides.

Adding a scenario must not require generator source-code changes.

---

# 31. Specification Substitution Test

This is the primary architectural test.

The experiment should execute materially different specifications using
the exact same generation runtime.

### Specification A

Baseline generation.

### Specification B

Change:

* population
* distributions
* categorical weights
* relationships
* rules
* dependencies
* scenarios

without changing generator source code.

Expected:

```text
Specification changed:       YES
Generator source changed:    NO
Generated behavior changed:  YES
Specification-driven:        PASS
```

This test is more important than simply generating a successful dataset.

---

# 32. Domain-Neutrality Test

The generator must operate on generic concepts such as:

```text
entity
field
type
semantic
strategy
distribution
identity
relationship
dependency
rule
scenario
```

It must not contain domain-specific concepts.

For example, the generator must not contain:

```python
if customer_type == "PREMIUM":
```

Instead, the specification should contain the equivalent semantic rule.

Likewise, a future:

```text
EMPLOYEE
ASSIGNMENT
PROJECT
```

model should be executable through the same generator without adding
employee-specific generation code.

---

# 33. Vocabulary Safety Test

Unknown vocabulary must be rejected.

Example:

```text
distribution = UNKNOWN_DISTRIBUTION
```

must fail validation.

The system must not:

* silently fall back
* guess another distribution
* ignore the declaration
* substitute a default implementation

Likewise, registered but unimplemented vocabulary must explicitly block
generation.

This becomes particularly important when FORGE later receives
specifications produced by an LLM.

---

# 34. Reproducibility Test

The experiment must demonstrate:

```text
same specification
+
same seed
+
same configuration
=
same generated output
```

Changing the seed should produce different values while preserving the
declared generation semantics.

The reproducibility context must be captured in the experiment evidence.

---

# 35. Experiment Variants

At minimum, the experiment should execute the following variants.

### Variant A: Baseline

Generate the complete six-entity relational model.

### Variant B: Distribution Change

Change one or more distributions through the specification.

### Variant C: Rule Change

Change a declared business constraint or derived calculation.

### Variant D: Relationship Change

Modify an optional relationship or relationship population.

### Variant E: Scenario Change

Generate the same model under different scenarios.

### Variant F: Invalid Specification

Introduce deliberate errors such as:

* unknown vocabulary
* invalid parameter
* missing reference
* circular dependency
* conflicting constraint

Generation must be blocked before dataset generation.

---

# 36. Validation Strategy

Validation occurs at multiple levels.

## Structural Validation

Validate:

* entities
* fields
* data types
* required fields
* identity
* uniqueness

## Relationship Validation

Validate:

* foreign keys
* cardinality
* optionality
* associative relationships

## Constraint Validation

Validate:

* field constraints
* cross-field constraints
* conditional constraints
* derived-value constraints

## Dependency Validation

Validate:

* parent dependencies
* child dependencies
* field dependencies
* temporal dependencies
* sequential dependencies

## Distribution Validation

Validate:

* expected distribution
* parameter boundaries
* categorical proportions
* numeric characteristics

## Statistical Validation

Validate:

* target correlation
* Pearson correlation
* Spearman correlation
* expected statistical behavior

## Provenance Validation

Validate:

* specification identity
* generation strategy
* parameters
* seed
* scenario
* dependency information
* validation evidence

---

# 37. Provenance / Evidence

Every generation run should produce evidence sufficient to understand how
the dataset was generated.

Evidence should include, where applicable:

* run identifier
* specification identity
* specification version
* seed
* scenario
* entity
* field
* generation strategy
* distribution
* parameters
* dependency
* relationship
* rule
* validation result

The objective is to make generated data explainable and auditable.

---

# 38. Expected Results

The experiment is expected to demonstrate that:

1. The complete vocabulary can be represented through a machine-readable
   registry.

2. The vocabulary can be composed into one declarative specification.

3. A realistic relational model can be represented without domain-specific
   generator logic.

4. Composite identities can be declared and generated.

5. Natural and surrogate identities can coexist.

6. Relationships can be declared and generated generically.

7. N:M relationships can be materialized through associative entities.

8. Dependencies can be represented and resolved into a generation plan.

9. Derived values can be represented declaratively.

10. Temporal dependencies can be represented declaratively.

11. Statistical behavior can be represented and validated.

12. Scenarios can modify behavior without generator changes.

13. Invalid specifications are rejected safely.

14. Unknown vocabulary is rejected safely.

15. Generated output can be validated against the specification.

16. Provenance can explain generation.

17. Reproducibility can be demonstrated.

18. Multiple materially different specifications can execute through the
    same generation engine.

19. Generator source code does not change when generation requirements
    change.

---

# 39. Failure Conditions

The experiment fails architecturally if:

* vocabulary elements require domain-specific generation logic
* specifications contain executable implementation code
* generation order must be manually hard-coded
* composite identity requires entity-specific implementation
* relationship generation requires domain-specific branches
* rules cannot be composed
* temporal dependencies cannot be represented
* derived values require special-case code
* unknown vocabulary is silently accepted
* invalid specifications reach generation
* specification changes require generator source changes
* provenance cannot explain generation
* reproducibility cannot be demonstrated

A vocabulary item being registered but not yet implemented is not itself a
failure, provided FORGE explicitly reports it and safely blocks generation.

---

# 40. Success Criteria

## Vocabulary

* [ ] Complete Controlled Vocabulary v1 represented
* [ ] Central registry implemented
* [ ] Vocabulary metadata available
* [ ] Vocabulary lifecycle status available
* [ ] Unknown vocabulary rejected

## Specification

* [ ] Declarative specification implemented
* [ ] Primitive types represented
* [ ] Semantic types represented
* [ ] Generation strategies represented
* [ ] Distributions represented
* [ ] Identity represented
* [ ] Composite keys represented
* [ ] Relationships represented
* [ ] Dependencies represented
* [ ] Rules represented
* [ ] Scenarios represented
* [ ] Statistical behavior represented
* [ ] Generation controls represented

## Relational Model

* [ ] 1:1 relationship
* [ ] 1:N relationship
* [ ] 0:N relationship
* [ ] N:M relationship
* [ ] Optional relationship
* [ ] Parent dependency
* [ ] Child dependency
* [ ] Composite identity
* [ ] Natural identity
* [ ] Surrogate identity

## Planning

* [ ] Dependency graph generated
* [ ] Generation order derived
* [ ] Circular dependencies detected
* [ ] Generation plan persisted
* [ ] Generation plan inspectable

## Generation

* [ ] Generic field generation
* [ ] Generic distribution execution
* [ ] Generic identity generation
* [ ] Generic relationship generation
* [ ] Generic rule execution
* [ ] Generic dependency execution
* [ ] Generic scenario execution
* [ ] Generic derived-value execution

## Validation

* [ ] Structural validation
* [ ] Relationship validation
* [ ] Constraint validation
* [ ] Dependency validation
* [ ] Distribution validation
* [ ] Statistical validation
* [ ] Provenance validation

## Evidence

* [ ] Run provenance
* [ ] Specification identity
* [ ] Generation evidence
* [ ] Validation evidence
* [ ] Reproducibility evidence

## Architecture

* [ ] Specification substitution passes
* [ ] Domain-neutrality passes
* [ ] Generator source remains unchanged
* [ ] Same generator executes different specifications

---

# 41. Relationship to Previous Experiments

Experiments 001-019 established individual FORGE capabilities.

Important foundations include:

| Experiment | Capability                        |
| ---------- | --------------------------------- |
| 007        | Reproducibility                   |
| 008        | Generation Strategy Abstraction   |
| 009        | Population                        |
| 010        | Composite Identity                |
| 011        | Cross-Field Constraints           |
| 012        | Correlation and Dependency        |
| 013        | Relationship Model Expansion      |
| 014        | Parent-Dependent Generation       |
| 015        | Scenario Generation               |
| 016        | Statistical Generation Validation |
| 017        | Unified Validation                |
| 018        | Constraint Conflict Detection     |
| 019        | Generation Evidence / Provenance  |

Those experiments primarily asked:

> Can FORGE perform this capability?

Experiment 020 asks:

> Can these capabilities be composed through one coherent declarative
> language and executed by one generic generation architecture?

---

# 42. Architectural Significance

Experiment 020 is the bridge between the capability experiments and the
FORGE core framework.

The architectural boundary is:

```text
                    USER INTENT
                         |
             +-----------+-----------+
             |                       |
        Direct Spec             Future UI / LLM
             |                       |
             +-----------+-----------+
                         |
                         v
                FORGE Specification
                         |
                         v
                Vocabulary Registry
                         |
                         v
             Specification Validation
                         |
                         v
                 Dependency Graph
                         |
                         v
                 Generation Plan
                         |
                         v
                Generic Generator
                         |
                         v
                 Synthetic Dataset
                    /          \
                   /            \
                  v              v
             Validation      Provenance
```

The central architectural principle is:

> **The specification contains intent. The generation engine contains
> execution.**

---

# 43. Future Evolution

The intended progression is:

```text
Experiments 001-019
        |
        v
020 - Declarative Generation Specification
        |
        v
021 - Specification Validation / Compilation
        |
        v
022 - Natural Language -> FORGE Specification
        |
        v
FORGE Core Framework
```

The future LLM layer should not generate synthetic data directly.

It should translate natural language into a candidate FORGE specification.

That specification must then pass deterministic FORGE validation.

```text
Natural Language
       |
       v
      LLM
       |
       v
Candidate FORGE Specification
       |
       v
FORGE Validation
       |
       v
Generation Plan
       |
       v
Generic Generator
```

The LLM is therefore an interpretation layer, not the trusted generation
engine.

FORGE must remain safe when the LLM is wrong.

---

# 44. Non-Goals

This experiment does not attempt to build:

* graphical UI
* natural-language interpretation
* LLM integration
* machine-learning-based synthetic generation
* business-rule inference from sample datasets
* production APIs
* distributed generation
* cloud infrastructure
* enterprise deployment
* production-scale optimization

The objective is to establish the declarative generation foundation
before introducing those concerns.

---

# 45. How to Run

From the repository root:

```bash
uv run python experiments/020_declarative_generation_specification/experiment.py
```

---

# 46. Expected Output

Generated datasets, generation plans, validation results, provenance and
experiment statistics should be written to:

```text
experiments/020_declarative_generation_specification/output/
```

Expected structure:

```text
output/
├── generation_plan.json
├── dependency_graph.json
├── vocabulary_report.json
├── validation_results.json
├── provenance.json
├── experiment_statistics.json
├── baseline/
│   ├── CUSTOMER.csv
│   ├── CUSTOMER_PROFILE.csv
│   ├── PRODUCT.csv
│   ├── ORDER.csv
│   ├── ORDER_ITEM.csv
│   └── SHIPMENT.csv
├── specification_variant/
│   └── ...
└── invalid_specification/
    └── validation_result.json
```

The exact output structure may evolve during implementation.

---