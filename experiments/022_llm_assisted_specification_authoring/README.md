# Experiment 022: LLM-Assisted Specification Authoring

**Status:** Completed

**Experiment Type:** Specification Authoring / LLM Assistance / Validation

**FORGE Area:** Specification Authoring

**Objective:** Determine whether an LLM-assisted authoring workflow can help create and modify a structured FORGE specification while keeping the canonical specification deterministic, structured, validated, and under user control.

---

## 1. Research Question

Can an LLM assist a user in creating and modifying a structured FORGE specification without becoming the source of truth for the specification?

The experiment evaluates whether natural-language intent can be translated into structured specification changes while maintaining:

- explicit generation rules,
- explicit relationships,
- explicit identities,
- explicit constraints,
- deterministic structured output,
- specification validation,
- and user control over the final specification.

The experiment does not evaluate synthetic dataset generation.

---

## 2. Hypothesis

An LLM can assist with specification authoring when its output is treated as a proposal rather than as an authoritative execution definition.

The intended authoring model is:

```text
User Intent
     │
     ▼
LLM Assistance
     │
     ▼
Suggested Specification Change
     │
     ▼
User Review / Modification
     │
     ▼
Canonical specification.json
     │
     ▼
FORGE Specification Validation
````

The LLM therefore assists authoring but does not directly execute generation.

The canonical specification remains the source of truth.

---

## 3. Experiment Boundary

Experiment 022 is responsible for specification authoring.

```text
022 Specification Authoring
          │
          │ specification.json
          ▼
023 Population Planning
          │
          │ population plan
          ▼
024 Specification Execution
          │
          ├── Generation
          └── Independent Validation
```

The experiment ends when a valid, approved specification is available for downstream experiments.

022 does not own:

* population feasibility planning,
* dataset generation,
* generation checkpointing,
* dataset validation,
* final dataset assembly,
* or synthetic data quality evaluation.

Those concerns belong to downstream execution stages.

---

## 4. Authoring Model

The central design principle is:

> The LLM proposes. The user approves. FORGE validates and executes.

The LLM is not trusted as the final authority over the specification.

A proposed change must ultimately become an explicit structured specification element.

For example:

```text
Natural-language intent
        │
        ▼
LLM suggestion
        │
        ▼
Structured field / relationship / constraint
        │
        ▼
User approval
        │
        ▼
Canonical specification
```

This keeps the resulting specification inspectable and executable without requiring the LLM to remain present during downstream execution.

---

## 5. Canonical Specification

The authoritative output of Experiment 022 is:

```text
experiments/022_llm_assisted_specification_authoring/output/specification.json
```

This file is the hand-off artifact to Experiment 023.

The canonical specification contains structured definitions for:

* entities,
* fields,
* field types,
* identities,
* generation rules,
* semantic generation,
* constraints,
* relationships,
* foreign keys,
* and population requirements.

The specification is designed to be consumed without requiring the authoring application or LLM.

---

## 6. Specification Structure

The specification represents the executable intent of the authoring stage.

Conceptually:

```text
Specification
│
├── Entities
│   ├── Identity
│   ├── Fields
│   │   ├── Type
│   │   ├── Generation
│   │   ├── Semantics
│   │   └── Constraints
│   │
│   ├── Relationships
│   └── Foreign Keys
│
└── Population Requirements
```

A field may contain explicit generation metadata.

Example:

```json
{
  "name": "PRODUCT_GROUP",
  "type": "STRING",
  "generation": {
    "generator": "SEMANTIC",
    "parameters": {
      "description": "Realistic aerospace product group or product category names.",
      "mode": "VOCABULARY"
    }
  }
}
```

Semantic generation is therefore represented as specification metadata.

The execution engine does not need to infer the intended semantic behavior from the original natural-language request.

---

## 7. Semantic Generation Authoring

The experiment established explicit semantic generation modes.

### VOCABULARY

Produces reusable semantic values where repetition is expected.

Example:

```text
Avionics Systems
Propulsion Systems
Airframe Structures
Landing Gear Assemblies
```

### UNIQUE

Produces semantic base values that are used to construct unique record-level values during execution.

Example:

```text
Avionics Systems 000001
Propulsion Systems 000002
Airframe Structures 000003
```

The authoring UI allows the user to explicitly select the semantic mode.

The resulting specification stores:

```json
{
  "generator": "SEMANTIC",
  "parameters": {
    "description": "...",
    "mode": "UNIQUE"
  }
}
```

or:

```json
{
  "generator": "SEMANTIC",
  "parameters": {
    "description": "...",
    "mode": "VOCABULARY"
  }
}
```

This makes semantic behavior explicit and reviewable.

---

## 8. Relationship and Foreign-Key Authoring

Relationships are explicitly represented in the specification.

A relationship identifies the source field(s) and referenced field(s).

Conceptually:

```text
Child Entity
    │
    │ Foreign Key
    ▼
Parent Entity Identity
```

Once a field is governed by an explicit foreign-key relationship, the relationship becomes the authoritative source of its value during execution.

The authoring layer therefore represents the relationship explicitly rather than expecting the execution engine to infer business relationships.

Composite relationships are represented using complete field sets.

Example:

```text
Child:
    (ORDER_ID, ITEM_NO)

Parent:
    (ORDER_ID, ITEM_NO)
```

The relationship definition remains part of the canonical specification.

---

## 9. Specification Validation

The authoring stage validates the canonical specification before it is handed downstream.

Validation checks the structural and semantic consistency of the specification.

The validation layer covers applicable areas including:

* entity definitions,
* field definitions,
* field types,
* identity definitions,
* generation configuration,
* semantic generation configuration,
* relationships,
* foreign keys,
* constraints,
* and population definitions.

The authoring UI and canonical specification validator must remain aligned with the current specification model.

A valid specification is required before the artifact is considered ready for downstream execution.

---

## 10. User Control

The LLM does not directly modify the authoritative specification without passing through the authoring workflow.

The intended control model is:

```text
LLM
 │
 ▼
Suggestion
 │
 ▼
User Review
 │
 ├── Accept
 ├── Modify
 └── Reject
 │
 ▼
Canonical Specification
 │
 ▼
FORGE Validation
```

This provides a clear boundary between AI assistance and executable configuration.

The final specification can therefore be inspected, versioned, validated, and executed independently of the LLM.

---

## 11. Experiment Results

The experiment successfully established an LLM-assisted authoring workflow capable of producing the canonical FORGE specification used by downstream experiments.

The final specification includes the current 21-entity execution stress model and exercises:

* multiple entities,
* entity identities,
* composite identities,
* relationships,
* foreign keys,
* composite foreign keys,
* multiple generation strategies,
* semantic generation,
* constraints,
* and population requirements.

The final canonical specification is:

```text
experiments/022_llm_assisted_specification_authoring/output/specification.json
```

The specification passed the final authoring validation:

```text
FORGE 022 AUTHORING VALIDATION

Errors: 0

AUTHORING VALIDATION: PASS
```

The canonical specification was subsequently consumed by Experiment 024 and successfully executed through the full generation and validation pipeline.

---

## 12. Downstream Handoff

The authoritative handoff from Experiment 022 is:

```text
output/specification.json
```

The downstream flow is:

```text
022
Specification Authoring
        │
        │ specification.json
        ▼
023
Population Planning
        │
        │ population requirements
        ▼
024
Specification Execution
        │
        ├── Generation
        └── Independent Validation
```

The authoring experiment therefore does not need to remain active during dataset execution.

Once the specification has been approved and validated, it becomes a standalone artifact.

---

## 13. Archived Specifications

Historical specifications used during the experiment are retained under:

```text
output/specifications/
```

Current archived artifacts include:

```text
sales_domain_stress_test_specification.json
sap_order_to_cash_chunking_stress_test_smoak_specification.json
sap_order_to_cash_chunking_stress_test_specification.json
sap_sales_order_model_specification.json
```

These files represent earlier experiment states and are not the authoritative production handoff.

The authoritative specification is:

```text
output/specification.json
```

A timestamped pre-semantic version is also retained:

```text
output/specification_before_semantic_20260921_121338.json
```

---

## 14. Experiment Boundary and Production Direction

Experiment 022 demonstrates the authoring concept.

The future FORGE application should provide stronger authoring guardrails than the experiment itself.

In particular, production authoring should constrain users to supported concepts such as:

1. Independent fields
2. Primary / unique identities
3. Foreign keys
4. Composite foreign keys
5. Supported field-generation strategies
6. Supported semantic modes
7. Supported constraints

The production application should prevent contradictory configurations rather than exposing the full flexibility of the underlying specification model.

For example, a field managed by a foreign-key relationship should not simultaneously expose an independent value-generation strategy as though it were unrelated to the parent.

These are application-level authoring controls.

They do not need to be expanded within Experiment 022.

---

## 15. Project Structure

```text
experiments/022_llm_assisted_specification_authoring/
│
├── README.md
├── README-experiment-outcome.md
├── app.py
├── experiment.py
│
└── output/
    ├── README.md
    ├── specification.json
    ├── specification_before_semantic_20260921_121338.json
    │
    └── specifications/
        ├── sales_domain_stress_test_specification.json
        ├── sap_order_to_cash_chunking_stress_test_smoak_specification.json
        ├── sap_order_to_cash_chunking_stress_test_specification.json
        └── sap_sales_order_model_specification.json
```

---

## 16. Run the Experiment

Run Experiment 022 from the FORGE repository root:

```bash
python experiments/022_llm_assisted_specification_authoring/app.py
```

The application provides the specification authoring workflow and validation.

The canonical specification is written to:

```text
experiments/022_llm_assisted_specification_authoring/output/specification.json
```

---

## 17. Final Experiment Status

```text
LLM-ASSISTED AUTHORING       : PASS
CANONICAL SPECIFICATION      : PASS
SPECIFICATION VALIDATION     : PASS
SEMANTIC AUTHORING           : PASS
RELATIONSHIP AUTHORING       : PASS
USER APPROVAL BOUNDARY       : PASS
DOWNSTREAM HANDOFF           : PASS

EXPERIMENT 022               : COMPLETED
```

The experiment establishes the specification-authoring foundation for FORGE.

The canonical specification produced here is the input contract for downstream population planning and specification execution.
"""

path.write_text(content, encoding="utf-8")
print(f"Updated: {path}")
print(f"Lines: {len(content.splitlines())}")
PY

````

Then test just this README:

```bash
python - <<'PY'
from pathlib import Path

path = Path("experiments/022_llm_assisted_specification_authoring/README.md")
text = path.read_text(encoding="utf-8")

required = [
    "# Experiment 022: LLM-Assisted Specification Authoring",
    "## 1. Research Question",
    "## 3. Experiment Boundary",
    "## 5. Canonical Specification",
    "## 7. Semantic Generation Authoring",
    "## 8. Relationship and Foreign-Key Authoring",
    "## 9. Specification Validation",
    "## 10. User Control",
    "## 11. Experiment Results",
    "## 12. Downstream Handoff",
    "## 13. Archived Specifications",
    "## 14. Experiment Boundary and Production Direction",
    "## 17. Final Experiment Status",
]

for section in required:
    assert section in text, f"Missing section: {section}"

canonical = Path(
    "experiments/022_llm_assisted_specification_authoring/output/specification.json"
)
assert canonical.exists(), "Canonical specification is missing"

assert "Errors: 0" in text
assert "AUTHORING VALIDATION: PASS" in text
assert "EXPERIMENT 022               : COMPLETED" in text

print("022 README structure      : PASS")
print("022 canonical handoff     : PASS")
print("022 validation evidence   : PASS")
print("022 final status          : PASS")
PY
````