FORGE
DOMAIN-NEUTRAL SPECIFICATION TEMPLATE
=====================================

PURPOSE
-------
This template is a practical reference for defining a data model using
the five CSV sections supported by the FORGE Specification Wizard.

The entity and field names are intentionally generic. Replace them
with names and definitions from your own data model.

CONTENTS
--------
01_entities.csv
02_fields_and_keys.csv
03_foreign_keys.csv
04_relationships.csv
05_constraints.csv

ENTITY EXAMPLES
---------------
ENTITY_1:
  Single-field identity. Demonstrates all field types and the
  executable field-generation configurations.

ENTITY_2:
  Composite identity. Demonstrates a single-field foreign key
  referencing ENTITY_1.

ENTITY_3:
  Single-field identity. Demonstrates a composite foreign key
  referencing ENTITY_2.

FIELD TYPES AND OPTIONS
-----------------------

1. UNIQUE ID
   CSV type: IDENTIFIER
   Identity strategy: SEQUENTIAL_ID
   Identity position: 1 for a single-field identity.
   Use positions 1, 2, ... for a composite identity.

2. TEXT
   CSV type: STRING
   Generation strategy: RANDOM

   Random Text:
     generator: RANDOM_STRING
     minimum_length: positive integer
     maximum_length: positive integer
     character_set:
       ALPHA
       DIGITS
       ALPHANUMERIC

   Pattern:
     generator: PATTERN
     pattern: one pattern string per field

     Pattern symbols:
       # = random digit
       A = random uppercase letter
       a = random lowercase letter
       X = random alphanumeric character
       Other characters are literals.

     Examples:
       ORD-####
       AA-####-aa
       ITEM-XXX-##

   Meaningful Text:
     generator: SEMANTIC
     semantic_description: natural-language description
     semantic_mode:
       VOCABULARY = reusable vocabulary
       UNIQUE = distinct value per record

3. WHOLE NUMBER
   CSV type: INTEGER
   Generation strategy: RANDOM

   Evenly Distributed:
     distribution: UNIFORM

   Whole Numbers Across a Range:
     distribution: DISCRETE_UNIFORM

   Both configurations use minimum and maximum whole-number values.

4. DECIMAL NUMBER
   CSV type: DECIMAL
   Generation strategy: RANDOM
   distribution: UNIFORM
   Uses minimum and maximum numeric values.

5. YES / NO
   CSV type: BOOLEAN
   Generation strategy: RANDOM
   No additional generation parameters.

6. CHOICE / CATEGORY
   CSV type: CATEGORICAL
   Generation strategy: RANDOM
   distribution: CATEGORICAL
   values: JSON array of distinct permitted values.

   Example:
     ["OPTION_A", "OPTION_B", "OPTION_C"]

IDENTITIES
----------
Every entity must have an identity.

Single-field identity:
  Set identity_position to 1.

Composite identity:
  Set identity_position to 1, 2, and so on.
  Positions must be contiguous and ordered.
  Each identity field uses type IDENTIFIER and
  identity_strategy SEQUENTIAL_ID.

FOREIGN KEYS
------------
Columns:
  source_entity, source_fields, target_entity

source_fields must be a JSON array.

The source field count and order must match the target entity's
identity fields. Field types must be compatible.

Examples:
  Single-field:
    ["ENTITY_2_FIELD_3"]

  Composite:
    ["ENTITY_3_FIELD_2", "ENTITY_3_FIELD_3"]

The target identity fields are derived by FORGE.

RELATIONSHIPS
-------------
Columns:
  source_entity, target_entity, type,
  source_participation, target_participation

Supported cardinality values:
  ONE_TO_ONE
  ONE_TO_MANY
  MANY_TO_ONE
  MANY_TO_MANY

Supported participation values:
  MANDATORY
  OPTIONAL

A relationship requires exactly one compatible foreign key
connecting the two entities under the current CSV importer.

CONSTRAINTS
-----------
Columns:
  entity, field, operator, value

Numeric fields (INTEGER and DECIMAL):
  >
  >=
  <
  <=

STRING and CATEGORICAL fields:
  ==
  !=

BOOLEAN constraints are not supported by the CSV importer.

POPULATION
----------
population_count:
  Requested number of records.

population_scaling:
  FIXED
  SCALABLE

Population planning assesses feasibility. It does not itself
allocate or generate records.

IMPORTANT IMPLEMENTATION NOTES
------------------------------
- Keep all five CSV headers unchanged.
- Leave unrelated configuration columns blank.
- Use one pattern per STRING field.
- Use JSON arrays for source_fields and categorical values.
- INTEGER minimum and maximum values must be whole numbers.
- Numeric ranges must have valid minimum and maximum values.
- Do not add generator settings to IDENTIFIER fields.
- BOOLEAN fields use generation_strategy RANDOM only.
- STRING fields use generator, not distribution.
- INTEGER fields support UNIFORM and DISCRETE_UNIFORM.
- DECIMAL CSV import currently supports UNIFORM only.
- The Model Studio UI displays Bell-Shaped decimal generation
  (NORMAL), but the current CSV importer rejects NORMAL for DECIMAL.
  Do not use NORMAL in this CSV template.
- NORMAL and POISSON are not executable decimal distributions
  through the current CSV importer.

WORKFLOW
--------
1. Download and extract this ZIP.
2. Use the examples as a reference when editing the CSV sections.
3. Paste each CSV's contents into its corresponding Wizard section.
4. Preview the proposed changes.
5. Resolve validation issues.
6. Apply the valid specification.

The examples demonstrate supported configurations. The FORGE Preview
and validation layers remain authoritative for a particular model.
