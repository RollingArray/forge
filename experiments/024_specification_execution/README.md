# Experiment 024: Specification Execution

**Status:** Completed

**Experiment Type:** Foundational / Generation / Relationship / Validation / Resilience

**FORGE Area:** Specification Execution

**Objective:** Determine whether FORGE can execute an approved specification to generate a synthetic dataset while preserving identity, relationship, constraint, population, and semantic-generation requirements, with independent validation and durable execution state.

---

## 1. Research Question

Can FORGE execute a structured specification and produce a complete synthetic dataset while preserving the rules explicitly declared by that specification?

The experiment also evaluates whether:

- generation can proceed in dependency order,
- generation can be performed in chunks,
- generation state can survive process interruption,
- committed output can be resumed safely,
- semantic field generation can be incorporated into normal execution,
- generated data can be independently validated,
- and validation remains separate from generation and does not repair generated data.

The experiment intentionally does not assume that every specification is executable.

---

## 2. Hypothesis

FORGE can execute an approved specification through a structured generation pipeline that produces a synthetic dataset satisfying the applicable identity, relationship, constraint, population, and field-generation requirements explicitly declared by the specification.

The hypothesis assumes:

- The specification has already been structurally defined and approved.
- Entity identities are explicitly defined.
- Relationships and foreign keys are explicitly defined.
- Generation dependencies can be resolved from the specification.
- Population requirements are available before generation begins.
- Generation can proceed in dependency order.
- Generated values can be produced from field metadata and generation rules.
- Semantic generation can be used where explicitly configured.
- Validation can independently inspect the generated dataset after generation.

---

## 3. Scope

This experiment evaluates the execution layer of FORGE.

### Included

- Loading the authoritative FORGE specification
- Building a generation plan
- Resolving entity dependencies
- Preparing generation context
- Generating entity records
- Dependency-ordered generation
- Chunked generation
- Maintaining generation context across entities and chunks
- Identity generation and uniqueness
- Foreign-key resolution
- Composite foreign-key resolution
- Field and constraint handling
- Semantic field generation
- Durable chunk output
- Atomic chunk commits
- Generation checkpoints
- Resume after interrupted execution
- Final entity dataset assembly
- Independent dataset validation
- Validation evidence and reporting
- Execution and quality evidence

### Excluded

- LLM-assisted specification authoring
- Population planning implementation
- Human approval workflows
- Production UI/API implementation
- Enterprise orchestration
- Distributed execution
- Automatic specification modification
- Automatic repair of invalid generated data
- Inference of undocumented business relationships
- Automatic attribute propagation between unrelated fields

These concerns belong outside the execution experiment and, where applicable, are addressed by other experiments or the future FORGE application.

---

## 4. Experiment Boundary

The experiment validates the execution stage of the FORGE flow:

```text
Specification
     │
     ▼
Requirement / Feasibility Analysis
     │
     ▼
Generation Planning
     │
     ▼
Generation
     │
     ▼
Independent Validation
     │
     ▼
Dataset
````

Within the broader experiment sequence:

```text
022 Specification Authoring
          │
          │ specification.json
          ▼
023 Population Planning
          │
          │ population requirements
          ▼
024 Specification Execution
          │
          ├── Generation
          ├── Durable Output
          ├── Resume / Checkpoint
          └── Independent Validation
```

Experiment 024 executes the rules that are explicitly present in the specification.

It does not infer additional business semantics that are not declared.

For example, if two fields are not connected by a declared relationship or dependency, FORGE does not infer that their values should be propagated or correlated.

---

## 5. Authoritative Specification

Experiment 024 consumes the authoritative specification produced by Experiment 022:

```text
experiments/022_llm_assisted_specification_authoring/output/specification.json
```

The current specification is a 21-entity stress specification designed to exercise:

* entity dependencies,
* primary and composite identities,
* foreign keys,
* composite foreign keys,
* multiple field-generation strategies,
* semantic generation,
* chunked generation,
* validation,
* and larger population execution.

The specification is intentionally richer than a typical production authoring scenario.

Its purpose is to exercise the execution engine across a broad range of declared rules.

---

## 6. Generation Architecture

Generation is performed through an explicit execution plan.

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
Durable Chunk Output
      │
      ▼
Final Entity Assembly
      │
      ▼
Independent Validation
```

The generation context maintains the state required by dependent entities and by subsequent chunks.

Parent identity values are therefore available when dependent entities are generated.

---

## 7. Generation Planning

Before generation begins, FORGE builds a generation plan from the specification.

The plan identifies:

* entities,
* target populations,
* entity identities,
* relationships,
* foreign-key dependencies,
* relationship groups,
* constraints,
* generation order,
* and generation configuration.

The planner determines the order in which entities can be generated.

The planner does not generate records itself.

---

## 8. Generation

The generation engine produces records according to the execution plan.

### Identity Generation

Identity fields must remain unique within their entity population.

For composite identities, uniqueness applies to the complete identity combination.

Example:

```text
Identity = (ORDER_ID, ITEM_NO)
```

The complete combination must be unique even when individual field values may repeat.

### Field Generation

Fields are generated according to their declared generation configuration.

The experiment exercises multiple generation strategies including:

* identifiers,
* patterns,
* random strings,
* categorical values,
* numeric distributions,
* boolean values,
* and semantic values.

### Semantic Generation

Semantic generation is explicitly configured at the field level.

Two semantic modes are supported:

```text
VOCABULARY
UNIQUE
```

`VOCABULARY` produces reusable semantic values where repetition is expected.

Example:

```text
Avionics Systems
Propulsion Systems
Airframe Structures
```

`UNIQUE` uses semantic base values to construct unique record-level values.

Example:

```text
Avionics Systems 000001
Propulsion Systems 000002
```

The LLM is used only to assist semantic value generation. It does not modify the canonical specification and does not participate in dataset validation.

### Foreign-Key Resolution

Foreign-key values are resolved from explicitly declared relationships and referenced identities.

A field governed by a declared relationship is therefore generated from the relationship rather than independently generating an unrelated value.

---

## 9. Chunked Generation

The execution engine supports chunked generation.

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
Durable Chunk Output
       │
       ▼
Final Entity Assembly
```

Chunks are committed independently.

This provides:

* bounded generation units,
* durable progress,
* recovery after interruption,
* deterministic checkpoint state,
* and support for larger populations.

Generation context remains consistent across chunks so that:

* identity uniqueness is preserved,
* parent keys remain available,
* foreign-key assignments remain valid,
* and previously committed chunks are not regenerated during resume.

---

## 10. Durable Output

Generated chunks are treated as durable execution artifacts.

The execution output follows this structure:

```text
output/generated/FORGE-<job_id>/
│
├── ENTITY_A/
│   └── chunks/
│       ├── chunk_000001.csv
│       └── ...
│
├── ENTITY_B/
│   └── chunks/
│       ├── chunk_000001.csv
│       └── ...
│
├── ENTITY_A.csv
├── ENTITY_B.csv
└── ...
```

Each chunk is written atomically.

The final entity CSV is assembled only after generation for that entity has completed.

The final dataset is therefore derived from committed chunks rather than being incrementally written during generation.

Committed chunks are retained after final assembly.

---

## 11. Checkpoint and Resume

The execution engine maintains a durable checkpoint for committed generation chunks.

The checkpoint records:

* job identity,
* specification hash,
* seed,
* chunk size,
* target populations,
* completed chunks,
* and checkpoint update state.

After a chunk is successfully committed, the checkpoint is updated.

On restart, FORGE:

1. Loads the checkpoint.
2. Validates that the checkpoint belongs to the same execution configuration.
3. Verifies that checkpointed chunk files exist.
4. Restores completed rows into the generation context.
5. Restores identity state.
6. Skips completed chunks.
7. Continues generation from the remaining work.

If a checkpoint claims a chunk is complete but the committed chunk file is missing, execution fails safely rather than regenerating the missing chunk.

This prevents silent data loss or inconsistent resume state.

---

## 12. Independent Validation

Validation is performed after generation and final dataset assembly.

```text
Generated Dataset
        │
        ▼
Independent Validator
        │
        ├── Completeness
        ├── Schema
        ├── Identity Integrity
        ├── Foreign-Key Integrity
        ├── Constraint Compliance
        ├── Domain Validity
        ├── Null / Value Completeness
        └── Coverage
        │
        ▼
Validation Report
```

The validator is independent of the generation logic.

It:

* detects violations,
* records validation evidence,
* produces validation results,
* and does not repair generated data.

It does not:

* modify generated records,
* regenerate failed records,
* change the specification,
* or silently correct violations.

This separation allows validation to independently assess the generated dataset.

---

## 13. Validation Evidence

The validation framework evaluates the generated dataset across the following dimensions:

1. Generation completeness
2. Schema completeness
3. Identity integrity
4. Referential integrity
5. Constraint compliance
6. Domain/range validity
7. Null/value completeness
8. Validation coverage

The validation result is persisted as a JSON validation artifact under:

```text
experiments/024_specification_execution/output/validation/
```

Example:

```text
output/validation/
└── FORGE-<job_id>_validation.json
```

---

## 14. Experiment Results

The latest full execution successfully completed the current 21-entity stress specification.

```text
Job ID           : FORGE-E73FF8015BC1
Entities         : 21
Requested rows   : 138,120
Generated rows   : 138,120
Final status     : COMPLETED
Errors           : None
Elapsed          : 00:56
Throughput       : 2,434 rows/s
```

### Entity Results

```text
CUSTOMER                1000 / 1000
CUSTOMER_ADDRESS        1500 / 1500
PRODUCT                  500 / 500
SALES_ORG                 20 / 20
PLANT                    100 / 100
STORAGE_LOCATION         500 / 500
PRODUCT_PLANT           2000 / 2000
INVENTORY              10000 / 10000
SALES_ORDER              2500 / 2500
SALES_ITEM              10000 / 10000
ORDER_PARTNER             7500 / 7500
ORDER_STATUS              2500 / 2500
DELIVERY                  3000 / 3000
DELIVERY_ITEM            12000 / 12000
DELIVERY_EVENT            50000 / 50000
SHIPMENT                  3500 / 3500
SHIPMENT_ITEM            12000 / 12000
CARRIER                    500 / 500
INVOICE                    3000 / 3000
INVOICE_ITEM              12000 / 12000
PAYMENT                    4000 / 4000
```

### Validation Result

```text
Entities checked          : 21
Complete entities         : 21

Requested rows            : 138,120
Generated rows            : 138,120

Schema valid              : 21 / 21
Missing / unexpected      : 0

Identity rows checked     : 138,120
Unique identities         : 138,120
Duplicate identities      : 0

Relationships checked     : 29
Relationship rows checked : 226,500
Invalid foreign keys      : 0

Constraints checked      : 6
Constraint violations    : 0

Domain fields checked    : 34
Invalid domain values    : 0

Null fields checked      : 82
Missing required values  : 0

Validation errors        : 0
```

Overall:

```text
GENERATION : PASS
VALIDATION : PASS
```

---

## 15. Resume Results

Checkpoint and resume behavior was independently tested.

```text
Initial chunk 1 committed     : PASS
Checkpoint recorded chunk 1  : PASS
Fresh process simulated      : PASS
Chunk 1 restored/skipped     : PASS
Chunk 2 generated            : PASS
Checkpoint now [1, 2]        : PASS
Generated rows = target      : PASS
Resume job completed         : PASS
```

Missing-chunk safety was also verified:

```text
Checkpoint loaded             : PASS
Missing committed chunk found : PASS
Resume failed safely          : PASS
Missing chunk not regenerated : PASS
```

---

## 16. Semantic Generation Results

Semantic generation was verified both independently and through the full execution pipeline.

The current specification exercises both supported semantic modes:

```text
PRODUCT_NAME
    SEMANTIC / UNIQUE

PRODUCT_GROUP
    SEMANTIC / VOCABULARY
```

The execution successfully demonstrated:

* semantic values generated through the configured semantic service,
* semantic mode propagated from specification to execution,
* vocabulary values reused across records,
* unique semantic values remaining unique at record level,
* semantic generation working across chunks,
* final semantic values surviving final dataset assembly,
* and independent validation passing after semantic generation.

---

## 17. Success Criteria

Experiment 024 is considered successful because FORGE demonstrated that it can:

1. Load the authoritative specification.
2. Build a valid generation plan.
3. Resolve generation dependencies.
4. Generate the requested entity populations.
5. Preserve identity uniqueness.
6. Preserve declared foreign-key integrity.
7. Handle composite identities and composite foreign keys.
8. Apply applicable generation constraints.
9. Maintain generation context across entities.
10. Maintain generation context across chunks.
11. Generate semantic fields using configured modes.
12. Commit generated chunks durably.
13. Maintain durable checkpoint state.
14. Resume generation after interruption.
15. Detect missing committed chunks safely.
16. Assemble final entity datasets from committed chunks.
17. Independently validate the generated dataset.
18. Produce validation evidence and a validation report.
19. Complete the full 138,120-row execution successfully.

---

## 18. Known Boundary

Experiment 024 validates generation according to explicitly declared specification rules.

It does **not** infer undocumented business dependencies.

If a relationship, foreign key, dependency, or semantic rule is not declared in the specification, the execution engine does not invent one.

For example:

```text
Declared relationship
    │
    ▼
Relationship-managed value
    │
    ▼
Referenced parent identity
```

versus:

```text
No declared relationship
        │
        ▼
Configured field generation rule
```

This is intentional.

The experiment therefore does not introduce automatic attribute propagation or other inferred business relationships.

Such behavior, if required in the future, should first be represented explicitly as a supported specification concept and then handled through the appropriate authoring and execution controls.

---

## 19. Experiment Conclusion

Experiment 024 has demonstrated that the FORGE execution layer can take an approved specification and execute it through a complete generation lifecycle:

```text
Approved Specification
          │
          ▼
Generation Planning
          │
          ▼
Dependency-Ordered Generation
          │
          ▼
Chunked Durable Execution
          │
          ▼
Checkpoint / Resume
          │
          ▼
Final Dataset Assembly
          │
          ▼
Independent Validation
          │
          ▼
Validated Synthetic Dataset
```

The experiment has therefore established the core execution foundation required for FORGE.

Further production-oriented concerns such as authoring guardrails, constrained user workflows, application UX, and API integration should be addressed in the actual FORGE application rather than expanded within this experiment.

---

## 20. Project Structure

```text
experiments/024_specification_execution/
│
├── README.md
├── app.py
├── experiment.py
│
├── generation/
│   ├── __init__.py
│   ├── checkpoint.py
│   ├── chunking.py
│   ├── context.py
│   ├── executor.py
│   ├── generator.py
│   ├── job.py
│   ├── output.py
│   ├── planner.py
│   ├── progress.py
│   ├── relationship.py
│   ├── result.py
│   ├── semantic.py
│   ├── specification.py
│   └── validator.py
│
└── output/
    ├── generated/
    ├── validation/
    ├── quality/
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
| `semantic.py`      | Generate configured semantic values                  |
| `chunking.py`      | Partition populations into generation chunks         |
| `checkpoint.py`    | Persist and restore durable execution state          |
| `executor.py`      | Execute entity and chunk generation                  |
| `job.py`           | Manage execution lifecycle                           |
| `result.py`        | Represent generation results                         |
| `progress.py`      | Report execution progress                            |
| `output.py`        | Commit chunks and assemble final datasets            |
| `validator.py`     | Independently validate generated data                |
| `__init__.py`      | Generation package definition                        |

---

## 21. Run the Experiment

Run Experiment 024 from the FORGE repository root:

```bash
python experiments/024_specification_execution/app.py
```

Generated datasets are written under:

```text
experiments/024_specification_execution/output/generated/
```

Validation reports are written under:

```text
experiments/024_specification_execution/output/validation/
```

Quality artifacts are written under:

```text
experiments/024_specification_execution/output/quality/
```

Run evidence is captured in:

```text
experiments/024_specification_execution/output/run_result.md
```

To inspect generated datasets:

```bash
find experiments/024_specification_execution/output/generated \
  -maxdepth 3 \
  -type f \
  | sort
```

To inspect validation reports:

```bash
find experiments/024_specification_execution/output/validation \
  -maxdepth 1 \
  -type f \
  | sort
```

---

## 22. Final Experiment Status

```text
SPECIFICATION EXECUTION     : PASS
DEPENDENCY RESOLUTION       : PASS
IDENTITY INTEGRITY          : PASS
FOREIGN-KEY INTEGRITY       : PASS
CONSTRAINT VALIDATION       : PASS
SEMANTIC GENERATION         : PASS
CHUNKED GENERATION          : PASS
DURABLE OUTPUT              : PASS
CHECKPOINT / RESUME         : PASS
FINAL DATASET ASSEMBLY      : PASS
INDEPENDENT VALIDATION      : PASS

EXPERIMENT 024              : COMPLETED
```

"""

path.write_text(content, encoding="utf-8")
print(f"Updated: {path}")
print(f"Lines: {len(content.splitlines())}")
PY

````

Then **test only this file**, no code changes:

```bash
python - <<'PY'
from pathlib import Path

path = Path("experiments/024_specification_execution/README.md")

assert path.exists(), "README.md does not exist"

text = path.read_text(encoding="utf-8")

required_sections = [
    "# Experiment 024: Specification Execution",
    "## 1. Research Question",
    "## 8. Generation",
    "## 9. Chunked Generation",
    "## 10. Durable Output",
    "## 11. Checkpoint and Resume",
    "## 12. Independent Validation",
    "## 14. Experiment Results",
    "## 15. Resume Results",
    "## 16. Semantic Generation Results",
    "## 18. Known Boundary",
    "## 19. Experiment Conclusion",
    "## 22. Final Experiment Status",
]

for section in required_sections:
    assert section in text, f"Missing section: {section}"

assert "138,120" in text
assert "FORGE-E73FF8015BC1" in text
assert "2,434 rows/s" in text
assert "VALIDATION errors" not in text
assert "ATTRIBUTE_PROPAGATION" not in text

print("024 README structure : PASS")
print("024 experiment results: PASS")
print("024 boundary          : PASS")
print("024 final status      : PASS")
PY
````
