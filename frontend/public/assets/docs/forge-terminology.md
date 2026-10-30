# FORGE Knowledge Guide

## Understanding specification-driven synthetic data generation

FORGE (Framework for Observed Rules, Generation & Engineered Data) uses an explicit specification to describe the structure, identity, relationships, constraints and population requirements of a dataset.

The specification is the engineering blueprint used to plan and generate synthetic data while preserving the rules defined by the user.

This guide explains FORGE concepts for both technical and business users.

---

# 1. Foundations

## Data Model

A data model describes the logical structure of the data to be generated. It identifies entities, their fields, identities, relationships and other rules.

**Example:** An order management data model might contain CUSTOMER, ORDER, ORDER_LINE and PRODUCT.

**In FORGE:** A Data Model is the workspace in which the specification is authored and maintained.

## Specification

A specification is the structured definition of a data model that FORGE uses as the source of truth for validation, population planning and generation.

It describes more than column names. It also captures identities, generation instructions, foreign keys, relationships, constraints and population requirements.

**Think of it as:** The engineering blueprint for the synthetic dataset.

## Entity

An entity represents a distinct business object or logical dataset within a data model.

**Examples:** CUSTOMER, PRODUCT, SALES_ORDER, EMPLOYEE.

An entity contains fields and has an identity. It can also have a population requirement and participate in relationships with other entities.

**Common mistake:** Treating an entity as just a table name. In FORGE, it is also the owner of field definitions, identity and population configuration.

## Field

A field is an individual attribute belonging to an entity. It describes one value in each record of that entity.

**Example:** CUSTOMER may contain CUSTOMER_ID, CUSTOMER_NAME, EMAIL_ADDRESS and CREDIT_LIMIT.

A field has a name and a data type. Depending on its purpose, it may also have identity or generation configuration.

## Population

Population is the number of records requested for an entity.

For example, CUSTOMER may request 10,000 records while PRODUCT requests 500 records.

Population requirements are considered during population planning. Requested counts and scaling rules influence whether a target dataset can be produced consistently.

---

# 2. Field Data Types

A field's data type defines the kind of value it can hold. The type also influences which generation configurations are valid.

| Type | Meaning | Example |
|---|---|---|
| IDENTIFIER | A field used to identify records | CUSTOMER_ID |
| STRING | Text values | CUSTOMER_NAME |
| INTEGER | Whole numbers | QUANTITY |
| DECIMAL | Numeric values with fractional parts | UNIT_PRICE |
| BOOLEAN | True or false | IS_ACTIVE |
| CATEGORICAL | A value selected from a defined set | ORDER_STATUS |

### IDENTIFIER

Used for a field that identifies a record or participates in an entity's identity.

In FORGE, identifier generation currently supports the `SEQUENTIAL_ID` identity strategy.

### STRING

Used for text values. FORGE supports random strings, pattern-based strings and semantic strings.

Examples include names, addresses, reference codes and descriptions.

### INTEGER

Used for whole-number values, such as quantities, counts and age.

The currently executable numeric distributions are `UNIFORM` and `DISCRETE_UNIFORM`.

### DECIMAL

Used for numeric values that may contain fractional parts, such as prices, percentages and measurements.

The currently executable distribution is `UNIFORM`.

### BOOLEAN

Used for values representing true or false conditions.

### CATEGORICAL

Used when a field must take one value from a defined list.

**Example:** An ORDER_STATUS field might allow `NEW`, `PROCESSING`, `SHIPPED` and `CANCELLED`.

The allowed values must be supplied as a non-empty list.

---

# 3. Identity and Record Uniqueness

## Identity

An identity is the field or combination of fields that uniquely identifies a record within an entity.

For example, CUSTOMER_ID may uniquely identify each CUSTOMER record.

Every entity in a valid FORGE specification must have at least one identity field.

## Primary Identity

The primary identity is the configured identity of an entity. It provides the reference used to distinguish one record from another and is important when other entities refer to it.

## Composite Identity

A composite identity uses more than one field together to uniquely identify a record.

**Example:** An ORDER_LINE entity may use ORDER_ID and LINE_NUMBER together.

Neither field necessarily identifies a line by itself. The combination does.

## Identity Position

For a composite identity, identity position specifies the order of the fields in the identity.

| Field | Identity position |
|---|---:|
| ORDER_ID | 1 |
| LINE_NUMBER | 2 |

The positions must be distinct and define the identity's field order.

## Identity Strategy

The identity strategy defines how an identity value is produced.

The currently defined strategy is:

- `SEQUENTIAL_ID`: produces sequential identifier values.

Identity configuration is distinct from ordinary field generation configuration. An IDENTIFIER field uses identity configuration rather than a normal generation distribution.

---

# 4. Field Generation

Generation configuration tells FORGE how to produce values for a field.

It is separate from the field's data type and identity configuration.

## Generation Strategy

The generation strategy identifies the broad method used to produce values.

The currently defined strategy is:

- `RANDOM`: generates values using the configured field type and generation settings.

## String Generators

STRING fields support three generator choices.

### RANDOM_STRING

Generates random text using a configured length range and character set.

Configuration:

- `minimum_length`: shortest generated string length.
- `maximum_length`: longest generated string length.
- `character_set`: permitted characters.

Supported character sets:

| Value | Meaning |
|---|---|
| `ALPHA` | Alphabetic characters |
| `DIGITS` | Numeric digits |
| `ALPHANUMERIC` | Alphabetic characters and digits |

### PATTERN

Generates strings from a pattern.

The pattern can combine special symbols and literal characters.

| Symbol | Meaning |
|---|---|
| `#` | Random digit |
| `A` | Random uppercase letter |
| `a` | Random lowercase letter |
| `X` | Random alphanumeric character |

All other characters are treated as literals.

**Example:** `ORD-####-AA` produces values resembling `ORD-4821-QM`.

### SEMANTIC

Generates text based on a natural-language description of the intended value.

Configuration:

- `semantic_description`: describes what the value should represent.
- `semantic_mode`: controls the expected variation.

Supported modes:

| Value | Meaning |
|---|---|
| `UNIQUE` | Produces distinct semantic values |
| `VOCABULARY` | Produces values from a vocabulary associated with the description |

**Example description:** `A realistic product category name`.

Semantic generation is different from random character generation. The description provides meaning, not just a shape or length.

---

# 5. Numeric Distributions and Categorical Values

A distribution describes how generated numeric values are selected within a configured range.

## UNIFORM

Selects values across a configured minimum and maximum range.

For INTEGER fields, values are whole numbers. For DECIMAL fields, fractional values are supported.

## DISCRETE_UNIFORM

Selects whole-number values across an integer range.

The current INTEGER generator implements this using integer selection. Its behaviour is currently the same as the INTEGER `UNIFORM` implementation.

## CATEGORICAL

Selects values from a supplied list of permitted values.

This is used for CATEGORICAL fields.

**Example:** `["NEW", "PROCESSING", "SHIPPED"]`.

## NORMAL and POISSON

These values exist in the shared distribution vocabulary, but they are not currently supported by the generation planner and scalar generation implementation.

Do not select them for executable specifications until FORGE explicitly supports them.

## Minimum and Maximum

Numeric generation requires a valid minimum and maximum range at execution time.

- Minimum is the lower bound.
- Maximum is the upper bound.
- Minimum must not exceed maximum.
- INTEGER bounds must be whole numbers.

A CSV import may accept incomplete generation parameters, but a specification that lacks required execution parameters may not be ready for generation.

---

# 6. Foreign Keys and Relationships

## Foreign Key

A foreign key connects fields in one entity to the identity fields of another entity.

It establishes which records in the source entity refer to records in the target entity.

**Example:**

- CUSTOMER has identity `CUSTOMER_ID`.
- ORDER contains `CUSTOMER_ID`.
- ORDER.CUSTOMER_ID refers to CUSTOMER.CUSTOMER_ID.

The foreign key allows FORGE to generate orders that refer to valid customers.

## Source Entity and Target Entity

- **Source entity:** The entity containing the referencing fields.
- **Target entity:** The entity whose identity is being referenced.

In the example above, ORDER is the source and CUSTOMER is the target.

## Source Fields and Target Fields

A foreign key maps one or more source fields to the target entity's identity fields.

The number and order of source fields must match the target identity fields.

## Single-Field Foreign Key

A single-field foreign key maps one source field to one target identity field.

**Example:** ORDER.CUSTOMER_ID references CUSTOMER.CUSTOMER_ID.

## Composite Foreign Key

A composite foreign key maps multiple source fields to the multiple fields of a composite target identity.

**Example:**

The target entity ORDER_LINE has identity:

1. ORDER_ID
2. LINE_NUMBER

An entity such as SHIPMENT_LINE can reference that identity using both fields in the same order.

The source and target field types must be compatible.

## Relationship

A relationship describes the business-level association between two entities.

It captures the cardinality and participation of the association.

In FORGE's current CSV import workflow, a relationship must have exactly one compatible foreign key connecting the two entities. The importer uses that foreign key to establish the relationship.

## Relationship Cardinality

| Value | Meaning | Example |
|---|---|---|
| `ONE_TO_ONE` | One record on each side is associated with one record on the other side | PERSON and PASSPORT |
| `ONE_TO_MANY` | One source record can be associated with multiple target records | CUSTOMER and ORDER |
| `MANY_TO_ONE` | Multiple source records can be associated with one target record | ORDER and CUSTOMER |
| `MANY_TO_MANY` | Multiple records on either side can be associated with multiple records on the other side | STUDENT and COURSE |

The direction matters. Always interpret cardinality from the declared source entity to the target entity.

## Participation

Participation indicates whether an entity's involvement in a relationship is mandatory or optional.

| Value | Meaning |
|---|---|
| `MANDATORY` | Participation is required |
| `OPTIONAL` | Participation is not required |

Source and target participation are configured separately.

**Example:** An ORDER may be required to reference a CUSTOMER, while a CUSTOMER may exist without any ORDER.

---

# 7. Constraints

## Constraint

A constraint is a rule that restricts the values a field may contain.

Constraints help describe valid data beyond what is expressed by a field's data type or generation configuration.

**Example:** An ORDER quantity must be greater than zero.

A constraint identifies:

- The entity.
- The field.
- The operator.
- The comparison value.

## Constraint Operators

| Operator | Meaning | Example |
|---|---|---|
| `>` | Greater than | QUANTITY > 0 |
| `>=` | Greater than or equal to | AGE >= 18 |
| `<` | Less than | DISCOUNT < 100 |
| `<=` | Less than or equal to | AGE <= 120 |
| `==` | Equal to | STATUS == ACTIVE |
| `!=` | Not equal to | STATUS != CANCELLED |

The currently supported CSV constraint operators depend on the field type:

| Field type | Supported operators |
|---|---|
| INTEGER | `>`, `>=`, `<`, `<=` |
| DECIMAL | `>`, `>=`, `<`, `<=` |
| STRING | `==`, `!=` |
| CATEGORICAL | `==`, `!=` |

BOOLEAN constraints are not currently supported by the CSV importer.

**Important:** A constraint is not the same as a generation parameter. A generation parameter tells FORGE how to produce a value. A constraint expresses a rule that the value must satisfy.

---

# 8. Population Planning

## Population Count

Population count is the requested number of records for an entity.

**Example:**

| Entity | Requested records |
|---|---:|
| CUSTOMER | 10,000 |
| PRODUCT | 500 |
| ORDER | 25,000 |

A population count can be omitted during authoring, but a missing count may leave the population plan unresolved or require further configuration.

## Population Scaling

Population scaling indicates whether an entity's population is fixed or can be scaled.

| Value | Meaning |
|---|---|
| `FIXED` | The population count is treated as fixed |
| `SCALABLE` | The population can participate in scaling decisions |

## Population Plan

The population plan evaluates whether the requested entity populations are feasible under the specification's rules.

It considers the configured populations and relevant dependencies and constraints.

**Important distinction:** Population planning is a feasibility assessment. It is not the generation of records and does not itself allocate or generate the final dataset.

## Feasible and Infeasible

- **FEASIBLE:** The requested population can be satisfied under the evaluated rules.
- **INFEASIBLE:** The requested population cannot be satisfied under the evaluated rules.
- **UNRESOLVED:** The available specification information is insufficient to determine feasibility.
- **AUTO:** The population is configured for automatic handling.

These statuses describe planning outcomes, not generation-job completion.

---

# 9. Authoring a Specification with CSV

FORGE supports specification authoring through five CSV sections. Each section describes a different part of the data model.

The sections work together. A field must belong to an entity, a foreign key must reference valid identity fields, and a relationship must have a compatible foreign key.

## 1. Entities

File: `01_entities.csv`

Defines the entities and their population requirements.

| Column | Purpose |
|---|---|
| `entity` | Entity name |
| `description` | Business description |
| `population_count` | Requested record count |
| `population_scaling` | `FIXED` or `SCALABLE` |

## 2. Fields and Keys

File: `02_fields_and_keys.csv`

Defines the fields, their types, identities and generation configuration.

| Column | Purpose |
|---|---|
| `entity` | Owning entity |
| `field` | Field name |
| `type` | Field data type |
| `identity_position` | Position in the entity identity; blank if not an identity field |
| `identity_strategy` | Identity generation strategy |
| `generation_strategy` | Field generation strategy |
| `distribution` | Numeric or categorical distribution |
| `generator` | String generator |
| `minimum`, `maximum` | Numeric bounds |
| `minimum_length`, `maximum_length` | String length bounds |
| `character_set` | String character set |
| `pattern` | Pattern for pattern-based strings |
| `semantic_description` | Meaning of semantic values |
| `semantic_mode` | `UNIQUE` or `VOCABULARY` |
| `values` | JSON array of permitted categorical values |

Only the columns relevant to a field's configuration need values. Keep other optional columns blank.

## 3. Foreign Keys

File: `03_foreign_keys.csv`

Defines references from source entities to target entity identities.

| Column | Purpose |
|---|---|
| `source_entity` | Entity containing the referencing fields |
| `source_fields` | JSON array of source field names |
| `target_entity` | Entity whose identity is referenced |

The target fields are derived from the target entity's configured identity. The source field list must have the same number of fields and matching field types.

## 4. Relationships

File: `04_relationships.csv`

Defines the business association between two entities.

| Column | Purpose |
|---|---|
| `source_entity` | Source entity |
| `target_entity` | Target entity |
| `type` | Relationship cardinality |
| `source_participation` | `MANDATORY` or `OPTIONAL` |
| `target_participation` | `MANDATORY` or `OPTIONAL` |

The current CSV importer requires exactly one compatible foreign key between the two entities.

## 5. Constraints

File: `05_constraints.csv`

Defines rules restricting field values.

| Column | Purpose |
|---|---|
| `entity` | Entity containing the field |
| `field` | Field being constrained |
| `operator` | Supported comparison operator |
| `value` | Comparison value |

The operator must be supported for the selected field type.

---

# 10. Preview and Apply

The CSV authoring workflow separates reviewing an import from changing the specification.

## Edit

The user can edit CSV content directly in the relevant section of the Specification Wizard.

## Preview

Preview parses the CSV and reports the proposed changes, validation issues and conflicts.

Review the preview before applying anything.

## Apply

Apply persists the valid import into the currently open Data Model.

The importer uses additive merge behaviour:

- New definitions are added.
- Existing identical definitions are treated as no-ops.
- Existing definitions that conflict with incoming definitions are reported as conflicts.
- Existing specification content is not replaced wholesale.

**Important:** Importing CSV does not create a new Data Model. It updates the specification of the Data Model currently open in the Wizard.

## Recommended Authoring Order

1. Define entities and population requirements.
2. Define fields and identities.
3. Define foreign keys.
4. Define relationships.
5. Define constraints.
6. Preview and resolve all issues.
7. Apply the import.
8. Review the resulting specification and population plan.

---

# 11. Generation and Data Integrity

## Generation

Generation is the execution process that produces synthetic records from an approved specification and generation configuration.

It uses the field definitions, identities, relationships, foreign keys, constraints and population requirements as inputs.

## Referential Integrity

Referential integrity means that references between entities remain valid.

For example, every ORDER.CUSTOMER_ID value must refer to an existing CUSTOMER identity.

FORGE uses foreign key definitions and dependency information to preserve these references during generation.

## Dependency Ordering

Some entities depend on records from other entities.

If ORDER references CUSTOMER, the generation process must account for CUSTOMER records when generating ORDER records.

Dependency ordering helps determine an appropriate generation sequence.

## Deterministic Generation

A deterministic generation run produces repeatable results when the same specification, configuration and seed are used.

The generation seed provides a controlled starting point for random generation.

## Chunking

Chunking divides large generation workloads into smaller units of work rather than attempting to process every record in one operation.

This supports execution of larger datasets.

## Checkpointing

A checkpoint records execution progress so that the generation process can track completed work and support recovery scenarios.

## Validation

Validation checks whether a specification or generated output conforms to the applicable rules.

It is distinct from population planning:

- Validation checks correctness against defined rules.
- Population planning evaluates whether requested populations are feasible.
- Generation produces the records.

---

# 12. Common Authoring Mistakes

| Mistake | Why it matters |
|---|---|
| An entity has no identity | Every entity must have at least one identity field |
| Identity position is duplicated | Composite identity positions must define a distinct order |
| A foreign key references a non-identity field | The target fields must match the target entity identity |
| Composite foreign key fields are in the wrong order | Source and target identity fields must correspond positionally |
| Source and target field types differ | Foreign key field types must be compatible |
| A relationship has no compatible foreign key | The current CSV importer requires exactly one compatible foreign key between the entities |
| A categorical field has no values | Categorical generation requires a non-empty list |
| Numeric bounds are missing | Numeric generation requires valid bounds at execution |
| A string pattern is empty | Pattern generation requires a non-empty pattern |
| A semantic field has no description | Semantic generation needs a description to establish meaning |
| An unsupported distribution is selected | A vocabulary value is not necessarily executable |
| A constraint uses an unsupported operator | Supported operators depend on field type |

## A Practical Rule

Define the structure first, then the rules connecting that structure, and finally the population and generation configuration.

When something fails, identify whether the issue belongs to:

1. Structure: entities and fields.
2. Identity: uniqueness and identity configuration.
3. Relationships: foreign keys and associations.
4. Rules: constraints and generation configuration.
5. Population: requested record counts and feasibility.
6. Execution: generation readiness and runtime configuration.

---

# 13. Quick Glossary

| Term | Plain-language meaning |
|---|---|
| Data Model | The workspace describing the dataset to be generated |
| Specification | The structured blueprint of the data model |
| Entity | A distinct business object or logical dataset |
| Field | An attribute belonging to an entity |
| Data Type | The kind of value a field can contain |
| Identity | The field or fields that uniquely identify a record |
| Composite Identity | An identity formed from multiple fields |
| Identity Position | The order of fields in a composite identity |
| Identity Strategy | The method used to produce identity values |
| Generation Strategy | The broad method used to generate field values |
| Generator | The specific mechanism used to produce values |
| Distribution | The rule governing how values are selected |
| Semantic Description | Natural-language meaning supplied for semantic generation |
| Semantic Mode | The variation mode used for semantic values |
| Foreign Key | A reference from source fields to a target identity |
| Relationship | A business association between two entities |
| Cardinality | The one-to-one or one-to-many nature of an association |
| Participation | Whether involvement in a relationship is mandatory or optional |
| Constraint | A rule restricting permitted field values |
| Population Count | The requested number of records for an entity |
| Population Scaling | Whether an entity's population is fixed or scalable |
| Population Plan | An assessment of whether requested populations are feasible |
| Referential Integrity | The validity of references between entities |
| Dependency Ordering | The order in which dependent entities are handled |
| Deterministic Generation | Repeatable generation using the same inputs and seed |
| Chunking | Dividing a large generation workload into smaller units |
| Checkpoint | A record of generation progress |
| Preview | Reviewing proposed specification changes before applying them |
| Apply | Persisting valid imported definitions into the current Data Model |

---

# 14. Vocabulary and Execution Status

A value being accepted by a model or import vocabulary does not automatically mean that the generation engine can execute it.

The following distinctions are important when authoring specifications.

| Capability | Current status |
|---|---|
| IDENTIFIER with SEQUENTIAL_ID | Supported |
| STRING with RANDOM_STRING | Supported |
| STRING with PATTERN | Supported |
| STRING with SEMANTIC | Supported through semantic generation |
| INTEGER with UNIFORM | Supported |
| INTEGER with DISCRETE_UNIFORM | Supported |
| DECIMAL with UNIFORM | Supported |
| BOOLEAN generation | Supported |
| CATEGORICAL with permitted values | Supported |
| NORMAL distribution | Defined in vocabulary; not currently executable |
| POISSON distribution | Defined in vocabulary; not currently executable |

This guide describes the current implementation, not a promise that every listed capability will remain unchanged in future versions.

For the most accurate permitted values and validation rules, the canonical FORGE specification models and generation implementation take precedence over illustrative examples in this guide.

---

# 15. Recommended Learning Path

If you are new to FORGE, follow this sequence:

1. Understand Data Models, entities and fields.
2. Learn field types and identity configuration.
3. Understand generation strategies and distributions.
4. Learn how foreign keys and relationships connect entities.
5. Add constraints and population requirements.
6. Author the five CSV sections.
7. Preview and apply the specification.
8. Review validation and population readiness.
9. Generate data and inspect the results.

**The central idea:** Define the system and its rules first. FORGE uses that specification to engineer data that respects the structure and relationships of the system.
