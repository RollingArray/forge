# Experiment 024 Output

This directory contains the execution artifacts produced by Experiment 024: Specification Execution.

Experiment 024 separates generated dataset artifacts from execution state, validation evidence, and quality results.

---

## 1. Output Structure

```text
output/
│
├── README.md
│
├── generated/
│   └── FORGE-<job_id>/
│       ├── <ENTITY>/
│       │   └── chunks/
│       │       ├── chunk_000001.csv
│       │       └── ...
│       │
│       ├── <ENTITY>.csv
│       └── ...
│
├── validation/
│   └── FORGE-<job_id>_validation.json
│
└── quality/
    └── FORGE-<job_id>_quality.json
````

The current completed execution is:

```text
FORGE-E73FF8015BC1
```

---

## 2. Generated Dataset

Generated datasets are stored under:

```text
output/generated/
```

Each execution receives a unique FORGE job identifier.

Current execution:

```text
output/generated/FORGE-E73FF8015BC1/
```

The generated dataset contains one final CSV file per entity.

Example:

```text
FORGE-E73FF8015BC1/
├── CUSTOMER.csv
├── CUSTOMER_ADDRESS.csv
├── PRODUCT.csv
├── SALES_ORDER.csv
├── SALES_ITEM.csv
└── ...
```

These final `<ENTITY>.csv` files are the primary dataset artifacts produced by the experiment.

---

## 3. Durable Chunk Output

Each entity also retains the chunks used during generation.

Example:

```text
FORGE-E73FF8015BC1/
└── CUSTOMER_ADDRESS/
    └── chunks/
        ├── chunk_000001.csv
        └── chunk_000002.csv
```

Chunks are durable execution artifacts.

They are:

* written atomically,
* committed independently,
* used as the source for final entity assembly,
* retained after final assembly,
* and used to support checkpoint/resume.

The final entity CSV is assembled from these committed chunks after generation completes.

---

## 4. Final Entity Dataset

The final entity dataset has the following relationship with the chunk output:

```text
Generation
    │
    ├── Chunk 1 ──┐
    ├── Chunk 2 ──┤
    ├── Chunk 3 ──┤
    └── ...       │
                  ▼
          Final Entity CSV
```

For example:

```text
CUSTOMER/
└── chunks/
    └── chunk_000001.csv

CUSTOMER.csv
```

The final CSV is a derived user-facing artifact.

The committed chunks remain available as durable execution evidence.

---

## 5. Checkpoint

The generation checkpoint is stored alongside the generated execution.

Current checkpoint:

```text
output/generated/FORGE-E73FF8015BC1_checkpoint.json
```

The checkpoint records durable generation progress, including:

* job identity,
* specification hash,
* seed,
* chunk size,
* entity targets,
* completed chunks,
* and checkpoint update state.

The checkpoint allows a new execution process to determine which committed chunks can be restored and which chunks still need to be generated.

A checkpoint does not replace the generated dataset.

It represents execution state.

---

## 6. Validation Output

Independent validation reports are stored under:

```text
output/validation/
```

Current validation report:

```text
output/validation/FORGE-E73FF8015BC1_validation.json
```

The validation report records:

* job identity,
* specification reference,
* generated dataset reference,
* validation status,
* validation errors,
* and validation evidence.

The validation evidence covers the applicable:

* completeness,
* schema,
* identity integrity,
* foreign-key integrity,
* constraints,
* domain validity,
* null/value completeness,
* and coverage.

Validation is read-only with respect to the generated dataset.

The validator does not repair or regenerate data.

---

## 7. Quality Output

Quality results are stored under:

```text
output/quality/
```

Current quality artifact:

```text
output/quality/FORGE-E73FF8015BC1_quality.json
```

The quality artifact captures the quality profile produced after successful generation and validation.

It is separate from the validation report.

The validation report answers whether the generated dataset satisfies the declared validation requirements.

The quality artifact captures additional dataset-level quality information produced by the execution pipeline.

---

## 8. Current Execution Evidence

The current full execution is:

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

Validation completed successfully:

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
Constraint violations     : 0

Domain fields checked     : 34
Invalid domain values     : 0

Null fields checked       : 82
Missing required values   : 0

Validation errors         : 0
```

Result:

```text
GENERATION : PASS
VALIDATION : PASS
```

---

## 9. Entity Output Summary

The completed execution contains the following final datasets:

| Entity           |        Rows | Chunk Count |
| ---------------- | ----------: | ----------: |
| CUSTOMER         |       1,000 |           1 |
| CUSTOMER_ADDRESS |       1,500 |           2 |
| PRODUCT          |         500 |           1 |
| SALES_ORG        |          20 |           1 |
| PLANT            |         100 |           1 |
| STORAGE_LOCATION |         500 |           1 |
| PRODUCT_PLANT    |       2,000 |           2 |
| INVENTORY        |      10,000 |          10 |
| SALES_ORDER      |       2,500 |           3 |
| SALES_ITEM       |      10,000 |          10 |
| ORDER_PARTNER    |       7,500 |           8 |
| ORDER_STATUS     |       2,500 |           3 |
| DELIVERY         |       3,000 |           3 |
| DELIVERY_ITEM    |      12,000 |          12 |
| DELIVERY_EVENT   |      50,000 |          50 |
| SHIPMENT         |       3,500 |           4 |
| SHIPMENT_ITEM    |      12,000 |          12 |
| CARRIER          |         500 |           1 |
| INVOICE          |       3,000 |           3 |
| INVOICE_ITEM     |      12,000 |          12 |
| PAYMENT          |       4,000 |           4 |
| **Total**        | **138,120** |     **129** |

The chunk count reflects the committed generation chunks retained for the current execution.

---

## 10. Output Contract

The output directories have distinct responsibilities.

| Directory / Artifact                  | Purpose                         | Primary Consumer   |
| ------------------------------------- | ------------------------------- | ------------------ |
| `generated/<job_id>/<ENTITY>.csv`     | Final generated dataset         | Dataset consumer   |
| `generated/<job_id>/<ENTITY>/chunks/` | Durable generation artifacts    | Execution / resume |
| `generated/<job_id>_checkpoint.json`  | Durable execution state         | Resume logic       |
| `validation/<job_id>_validation.json` | Independent validation evidence | Validation / audit |
| `quality/<job_id>_quality.json`       | Dataset quality profile         | Quality analysis   |

The final entity CSVs are the primary generated dataset artifacts.

The chunk files, checkpoint, validation report, and quality profile are execution evidence and supporting artifacts.

---

## 11. Retention of Execution Artifacts

Chunks are intentionally retained after final dataset assembly.

This provides evidence of:

* how the dataset was committed,
* which generation units were completed,
* and which execution state was available for resume.

The final dataset and its supporting execution artifacts therefore coexist:

```text
Final Dataset
     │
     ├── ENTITY.csv
     │
     ├── Committed Chunks
     │
     ├── Checkpoint
     │
     ├── Validation Report
     │
     └── Quality Profile
```

---

## 12. Output Boundary

The output directory stores artifacts produced by Experiment 024.

It does not define production storage architecture.

In particular, this experiment does not establish:

* enterprise dataset retention policies,
* production storage locations,
* access-control models,
* API contracts,
* catalog integration,
* lifecycle management,
* or production orchestration.

Those concerns belong to the actual FORGE application.

---

## 13. Current Artifact Set

For the completed execution, the important artifacts are:

```text
output/
├── generated/
│   ├── FORGE-E73FF8015BC1/
│   │   ├── <21 entity datasets>
│   │   ├── <durable committed chunks>
│   │   └── ...
│   │
│   └── FORGE-E73FF8015BC1_checkpoint.json
│
├── validation/
│   └── FORGE-E73FF8015BC1_validation.json
│
└── quality/
    └── FORGE-E73FF8015BC1_quality.json
```

This artifact set represents the completed execution evidence for Experiment 024.

---

## 14. Experiment Status

```text
GENERATION OUTPUT       : PASS
DURABLE CHUNKS          : PASS
CHECKPOINT              : PASS
FINAL DATASET ASSEMBLY  : PASS
VALIDATION REPORT       : PASS
QUALITY PROFILE         : PASS

EXPERIMENT 024 OUTPUT   : COMPLETE
```

"""

path.write_text(content, encoding="utf-8")
print(f"Updated: {path}")
print(f"Lines: {len(content.splitlines())}")
PY

````

Then test it:

```bash
python - <<'PY'
from pathlib import Path

path = Path("experiments/024_specification_execution/output/README.md")
text = path.read_text(encoding="utf-8")

required = [
    "# Experiment 024 Output",
    "## 2. Generated Dataset",
    "## 3. Durable Chunk Output",
    "## 5. Checkpoint",
    "## 6. Validation Output",
    "## 7. Quality Output",
    "## 8. Current Execution Evidence",
    "## 9. Entity Output Summary",
    "## 10. Output Contract",
    "## 12. Output Boundary",
    "## 14. Experiment Status",
]

for section in required:
    assert section in text, f"Missing section: {section}"

assert "FORGE-E73FF8015BC1" in text
assert "138,120" in text
assert "129" in text
assert "21" in text
assert "226,500" in text
assert "0" in text
assert "ATTRIBUTE_PROPAGATION" not in text

# Verify the documented current artifacts actually exist.
artifacts = [
    Path("experiments/024_specification_execution/output/generated/FORGE-E73FF8015BC1_checkpoint.json"),
    Path("experiments/024_specification_execution/output/validation/FORGE-E73FF8015BC1_validation.json"),
    Path("experiments/024_specification_execution/output/quality/FORGE-E73FF8015BC1_quality.json"),
]

for artifact in artifacts:
    assert artifact.exists(), f"Missing artifact: {artifact}"

print("024 output README structure : PASS")
print("024 current job evidence    : PASS")
print("024 artifact references     : PASS")
print("024 output boundary         : PASS")
PY
````