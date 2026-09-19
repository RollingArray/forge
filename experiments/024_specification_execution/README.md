# Experiment 024: Specification Execution

**Status:** In Progress

**Experiment Type:** Foundational / Structural / Generation / Relationship / Validation / Performance

**FORGE Area:** Specification Execution

**Objective:** Determine whether FORGE can execute an approved specification to generate a synthetic dataset while preserving identity, relationship, and constraint integrity and independently validating the resulting dataset.

---

## 1. Research Question

Can FORGE execute a structured specification to generate a synthetic dataset while preserving the populations, identities, relationships, and constraints defined by the specification?

The experiment also evaluates whether generation and validation can remain independently separated so that validation verifies the generated dataset without participating in its creation or repair.

---

## 2. Hypothesis

FORGE can execute an approved specification through a structured generation pipeline that produces a synthetic dataset satisfying the applicable identity, relationship, and constraint requirements.

The hypothesis assumes:

- The specification has already been structurally defined and approved.
- Entity identities are explicitly defined.
- Foreign-key relationships are explicitly defined.
- Generation dependencies can be resolved from the specification.
- Population requirements are available before generation begins.
- Generation can proceed in dependency order.
- Generated values can be produced from field metadata, semantics, and constraints.
- Validation can independently inspect the generated dataset after generation.

The experiment intentionally does not assume that every specification is executable.

The hypothesis will be rejected if FORGE cannot:

- Resolve generation dependencies
- Produce the requested entity populations
- Preserve identity uniqueness
- Preserve required foreign-key relationships
- Satisfy applicable field constraints
- Independently validate the generated dataset

---

## 3. Scope

This experiment will evaluate the execution of an approved FORGE specification through generation and independent validation.

### Included

- Loading the FORGE specification
- Building a generation plan
- Resolving entity generation dependencies
- Preparing generation context
- Generating entity records
- Generating records in dependency order
- Supporting chunked generation
- Maintaining generation context across entities and chunks
- Preserving identity uniqueness
- Resolving foreign-key values
- Applying field and constraint semantics
- Writing the generated dataset
- Independently validating the generated dataset
- Reporting generation and validation results

### Excluded

- LLM-assisted specification authoring
- Population planning logic
- Automatic modification of the source specification
- Automatic repair of invalid generated data
- Human approval workflows
- Production-scale distributed execution
- Enterprise orchestration
- UI/API implementation

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

The experiment consumes the authoritative FORGE specification produced by Experiment 022.

```text
experiments/022_llm_assisted_specification_authoring/output/specification.json
````

Population planning is handled separately by Experiment 023.

The intended FORGE execution flow is:

```text
022 Specification Authoring
          │
          │ specification.json
          ▼
023 Population Planning
          │
          │ population_plan.json
          ▼
024 Specification Execution
          │
          ├── Generation
          └── Validation
```

The current specification contains the following entities:

```text
KNA1
MARA
VBAK
VBAP
VBPA
ADRC
VBAK_STATUS
VBEP
```

### Entity Identities

| Entity      | Identity Fields  |
| ----------- | ---------------- |
| KNA1        | `KUNNR`          |
| MARA        | `MATNR`          |
| VBAK        | `VBELN`          |
| VBAP        | `VBELN`, `POSNR` |
| VBPA        | `VBELN`, `PARVW` |
| ADRC        | `ADDRNUMBER`     |
| VBAK_STATUS | `VBELN`          |
| VBEP        | `POSNR`, `VBELN` |

### Key Relationships

| Relationship                                | Type        |
| ------------------------------------------- | ----------- |
| `VBAK.KUNNR → KNA1.KUNNR`                   | Many-to-One |
| `VBAP.VBELN → VBAK.VBELN`                   | Many-to-One |
| `VBPA.VBELN → VBAK.VBELN`                   | Many-to-One |
| `VBPA.ADRNR → ADRC.ADDRNUMBER`              | Many-to-One |
| `VBAK_STATUS.VBELN → VBAK.VBELN`            | One-to-One  |
| `VBEP.(VBELN, POSNR) → VBAP.(VBELN, POSNR)` | Many-to-One |

The entity model is used to test dependency resolution, identity generation, foreign-key assignment, and relationship integrity.

---

## 5. Experiment Configuration

The execution engine consumes a structured FORGE specification.

The specification defines:

* Entities
* Entity identities
* Fields
* Field types
* Field semantics
* Constraints
* Relationships
* Foreign keys
* Population requirements
* Generation metadata

Example:

```json
{
  "entities": [
    {
      "name": "VBAK",
      "identity": {
        "fields": ["VBELN"]
      },
      "population": {
        "count": 10
      }
    }
  ]
}
```

Foreign-key relationships are explicitly represented in the specification.

Example:

```json
{
  "name": "FK_VBAP_VBAK",
  "source": {
    "entity": "VBAP",
    "fields": ["VBELN"]
  },
  "target": {
    "entity": "VBAK",
    "fields": ["VBELN"]
  }
}
```

The execution engine uses these definitions to establish generation dependencies and assign compatible foreign-key values.

---

## 6. Generation Architecture

Generation is performed through a planned execution flow rather than generating entities independently.

```text
Specification
      │
      ▼
Generation Plan
      │
      ▼
Dependency Resolution
      │
      ▼
Entity Generation
      │
      ├── Identity Generation
      ├── Field Generation
      ├── Semantic Generation
      ├── Constraint Handling
      └── Foreign-Key Resolution
      │
      ▼
Generation Context
      │
      ▼
Generated Dataset
```

The generation context maintains information required by dependent entities.

For example:

```text
KNA1
  │
  └── KUNNR keys
        │
        ▼
      VBAK
        │
        └── VBELN keys
              │
              ├── VBAP
              ├── VBPA
              └── VBAK_STATUS
```

This allows child entities to reference compatible parent identities rather than generating unrelated foreign-key values.

---

## 7. Generation Planning

Before records are generated, FORGE builds a generation plan from the specification.

The plan identifies:

* Entities
* Entity identities
* Foreign-key dependencies
* Relationship dependencies
* Constraint definitions
* Generation order
* Generation configuration

Dependency ordering ensures that required parent identity values are available before dependent child records are generated.

The generation planner does not generate records itself.

---

## 8. Generation

The generation engine is responsible for producing synthetic records according to the execution plan.

Generation includes:

### Identity Generation

Identity fields must remain unique within their entity population.

For composite identities, uniqueness applies to the complete identity combination.

Example:

```text
VBAP
Identity = (VBELN, POSNR)
```

The pair must be unique even if individual field values may repeat.

### Field Generation

Fields are generated according to their declared metadata and applicable semantics.

### Foreign-Key Resolution

Foreign-key fields are resolved against compatible identity values available from the referenced parent entity.

### Constraint Handling

Applicable constraints are incorporated during generation rather than relying on post-generation repair.

---

## 9. Chunked Generation

The execution engine supports generation in chunks.

```text
Entity Population
       │
       ▼
   Chunk Planner
       │
       ├── Chunk 1
       ├── Chunk 2
       ├── Chunk 3
       └── ...
       │
       ▼
Generation Context
       │
       ▼
Complete Entity Dataset
```

Chunking is intended to control memory usage and support larger populations.

Generation context must remain consistent across chunks so that:

* Identity uniqueness is preserved.
* Parent keys remain available.
* Foreign-key assignments remain valid.
* Previously generated records are not duplicated.

---

## 10. Independent Validation

Validation is performed after generation.

The validator is independent of the generation logic.

```text
Generated Dataset
        │
        ▼
Independent Validator
        │
        ├── Identity Validation
        ├── Foreign-Key Validation
        ├── Constraint Validation
        └── Population Validation
        │
        ▼
Validation Result
```

The validator detects violations.

It does not:

* Modify generated records
* Repair invalid records
* Regenerate failed records
* Change the specification

This separation allows the validation result to provide an independent assessment of generation correctness.

### Validation Results

Validation is performed independently after generation.

The current execution reports validation results to the console. The `output/validation/` directory is reserved for persisted validation artifacts as the validation output contract evolves.

Validation covers the applicable:

* Identity rules
* Foreign-key relationships
* Field constraints
* Population requirements

---

## 11. Expected Outputs

The experiment produces generated datasets under:

```text
experiments/024_specification_execution/output/generated/
```

Each execution receives a unique dataset identifier.

Example:

```text
FORGE-30A38B7CD67A
```

The generated dataset contains one CSV file per entity:

```text
experiments/024_specification_execution/output/generated/FORGE-30A38B7CD67A/
├── ADRC.csv
├── KNA1.csv
├── MARA.csv
├── VBAK.csv
├── VBAK_STATUS.csv
├── VBAP.csv
├── VBEP.csv
└── VBPA.csv
```

Validation output is currently reported through the execution result and console. The validation directory is reserved for persisted validation artifacts as that contract evolves.

---

## 12. Success Criteria

The experiment is considered successful if FORGE can:

1. Load the approved specification.
2. Build a valid generation plan.
3. Resolve generation dependencies.
4. Generate the requested entity populations.
5. Preserve identity uniqueness.
6. Preserve foreign-key integrity.
7. Apply applicable generation constraints.
8. Maintain generation context across entities.
9. Maintain generation context across chunks.
10. Produce a complete generated dataset.
11. Independently validate the generated dataset.
12. Report validation results without modifying the generated dataset.
13. Complete execution without generation or validation errors.

---

## 13. Current Result

The latest execution successfully generated a dataset containing:

```text
Job ID          : FORGE-30A38B7CD67A
Entities        : 8
Target rows     : 120
Total generated : 120
Progress        : 100.0%
Final status    : COMPLETED
Error           : None
```

### Entity Results

| Entity      | Generated | Status    |
| ----------- | --------: | --------- |
| KNA1        |   20 / 20 | COMPLETED |
| MARA        |   10 / 10 | COMPLETED |
| VBAK        |   10 / 10 | COMPLETED |
| VBAP        |   20 / 20 | COMPLETED |
| VBPA        |   20 / 20 | COMPLETED |
| ADRC        |   10 / 10 | COMPLETED |
| VBAK_STATUS |   10 / 10 | COMPLETED |
| VBEP        |   20 / 20 | COMPLETED |

### Validation Result

```text
VALIDATION PASSED

Identity uniqueness : PASS
Foreign keys        : PASS
Constraints         : PASS
```

### Overall Result

```text
GENERATION : PASSED
VALIDATION : PASSED
```

The generated dataset is persisted at:

```text
experiments/024_specification_execution/output/generated/FORGE-30A38B7CD67A/
```

The execution evidence is captured at:

```text
experiments/024_specification_execution/output/run_result.md
```

---

## 14. Project Structure

```text
experiments/024_specification_execution/
│
├── README.md
├── app.py
├── experiment.py
│
├── generation/
│   ├── __init__.py
│   ├── chunking.py
│   ├── context.py
│   ├── executor.py
│   ├── generator.py
│   ├── job.py
│   ├── output.py
│   ├── planner.py
│   ├── relationship.py
│   ├── result.py
│   ├── semantic.py
│   ├── specification.py
│   └── validator.py
│
└── output/
    ├── generated/
    │   ├── FORGE-7EE2079B52EE/
    │   └── FORGE-30A38B7CD67A/
    ├── validation/
    └── run_result.md
```

### Generation Package

| Module             | Responsibility                                       |
| ------------------ | ---------------------------------------------------- |
| `specification.py` | Load and represent the FORGE specification           |
| `planner.py`       | Build generation plans and dependency definitions    |
| `context.py`       | Maintain generation state and entity context         |
| `relationship.py`  | Resolve relationship and child distribution behavior |
| `generator.py`     | Generate entity and field values                     |
| `chunking.py`      | Partition populations into generation chunks         |
| `executor.py`      | Execute entity and chunk generation                  |
| `job.py`           | Manage execution lifecycle                           |
| `result.py`        | Represent generation results                         |
| `output.py`        | Write generated dataset output                       |
| `semantic.py`      | Optional semantic value generation                   |
| `validator.py`     | Independently validate generated data                |
| `__init__.py`      | Generation package definition                        |

---

## 15. Run the Experiment

Run Experiment 024 from the FORGE repository root:

```bash
python experiments/024_specification_execution/app.py
```

The experiment:

1. Loads the FORGE specification.
2. Creates a generation job.
3. Builds the generation plan.
4. Resolves entity dependencies.
5. Generates the requested populations.
6. Writes the generated entity datasets.
7. Runs independent dataset validation.
8. Reports generation and validation results.

Generated datasets are written under:

```text
experiments/024_specification_execution/output/generated/
```

Validation output is currently reported through the execution result.

Run evidence is captured in:

```text
experiments/024_specification_execution/output/run_result.md
```

To inspect generated datasets:

```bash
find experiments/024_specification_execution/output/generated \
  -maxdepth 2 \
  -type f \
  | sort
```

To inspect the validation output directory:

```bash
ls -lh experiments/024_specification_execution/output/validation/
```

---

## 16. Experiment Boundary

Experiment 024 is responsible for executing an approved specification.

```text
022 Specification Authoring
          │
          │ specification.json
          ▼
023 Population Planning
          │
          │ population_plan.json
          ▼
024 Specification Execution
          │
          ├── Generation
          │
          └── Independent Validation
```