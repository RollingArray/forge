# Experiment 022: LLM-Assisted Specification Authoring

**Status:** Planned

**Experiment Type:** Foundational / Validation

**FORGE Area:** Declarative Specification / Specification Authoring

**Objective:** Determine whether an LLM can assist a user in creating and refining a valid FORGE specification from natural-language requirements without changing or bypassing the existing FORGE specification contract.

---

## 1. Research Question

Can an LLM translate natural-language data requirements into the existing
FORGE declarative specification format, while remaining constrained to
the supported FORGE vocabulary, structure, relationships, constraints,
dependencies, and generation capabilities?

---

## 2. Hypothesis

An LLM can significantly reduce the effort required to author a FORGE
specification by translating natural-language requirements into the
existing declarative specification format.

The hypothesis is that the LLM can act as an authoring assistant while
the existing FORGE specification validation remains the authority for
determining whether the resulting specification is valid and executable.

The experiment assumes:

- The existing FORGE specification format is sufficient to represent
  the requirements being tested.
- The LLM is constrained to the existing FORGE specification structure
  and vocabulary.
- The LLM may propose values or structures based on user input.
- The user can review, correct, or manually modify the proposed
  specification.
- FORGE remains responsible for structural, semantic, feasibility, and
  execution validation.

The experiment intentionally does not assume that the LLM will always
understand an ambiguous requirement correctly.

The hypothesis will be rejected if the LLM cannot reliably produce
specifications that conform to the existing FORGE contract, or if
unsupported or invented constructs can reach the generation engine.

---

## 3. Scope

This experiment will test LLM-assisted creation and progressive
refinement of a FORGE specification, including validation of both
successful and adversarial authoring scenarios.

### Included

- Natural-language requirement to FORGE specification.
- Multiple entity and field definition.
- Population definition.
- Relationship definition.
- Constraint definition.
- Derived field definition.
- Conditional field definition.
- Dependency definition.
- Supported statistical behavior.
- Progressive refinement of an existing specification.
- User correction of an LLM proposal.
- Manual modification of an LLM-generated specification.
- Ambiguous requirement handling.
- Unsupported requirement handling.
- Invalid FORGE vocabulary handling.
- Contradictory requirement handling.
- Validation of the resulting specification using FORGE.
- Execution of an accepted specification using the existing generation
  capability.

### Excluded

- LLM-generated synthetic data.
- LLM-generated Python generation logic.
- A new specification language for the LLM.
- LLM bypass of FORGE validation.
- LLM-controlled dataset generation.
- Automatic acceptance of an LLM-generated specification.

These capabilities are intentionally outside the LLM authoring boundary.

---

## 4. Initial Dataset / Entity

The experiment will use a small domain-neutral relational model that is
complex enough to exercise entities, relationships, constraints,
dependencies, derived fields, and conditional behavior.

### Entity

`CUSTOMER`

### Fields

| Field | Type | Semantic / Behavior |
|---|---|---|
| CUSTOMER_ID | identifier | Sequential unique identifier |
| CUSTOMER_TYPE | categorical | Customer classification |
| CREDIT_LIMIT | numeric | Customer credit limit |
| CUSTOMER_STATUS | categorical | Derived from customer type |

### Entity

`PRODUCT`

### Fields

| Field | Type | Semantic / Behavior |
|---|---|---|
| PRODUCT_ID | identifier | Sequential unique identifier |
| CUSTOMER_ID | identifier | Relationship-managed reference |
| UNIT_PRICE | numeric | Positive generated value |
| QUANTITY | integer | Positive generated value |
| TOTAL_VALUE | numeric | Derived from UNIT_PRICE × QUANTITY |
| VALUE_BAND | categorical | Conditional classification based on TOTAL_VALUE |

The model will be represented using the existing FORGE
`specification.json` structure.

---

## 5. Experiment Configuration

The experiment will use the existing FORGE declarative specification
contract as the output contract for the LLM.

The LLM will receive natural-language requirements and will be expected
to produce only a FORGE-compatible specification.

The proposed specification will then pass through the existing
validation process before it can be executed.

Example flow:

```text
Natural-language requirement
            |
            v
      LLM proposal
            |
            v
   FORGE specification
            |
            v
 Specification validation
            |
            v
 Feasibility / conflict validation
            |
            v
      User review
            |
            v
 Existing FORGE generator
````

The LLM is therefore positioned only at the specification-authoring
boundary.

---

## 6. Experiment Tests

The experiment will test the following cases:

| Test                              | Expected Result                          |
| --------------------------------- | ---------------------------------------- |
| Simple natural-language request   | Valid specification                      |
| Multiple entities                 | Valid specification                      |
| Relationship requirement          | Valid relationship                       |
| Constraint requirement            | Valid constraint                         |
| Derived field requirement         | Valid dependency                         |
| Conditional requirement           | Valid conditional dependency             |
| Statistical behavior requirement  | Valid supported behavior                 |
| Progressive refinement            | Existing specification updated correctly |
| User correction                   | Correction reflected in specification    |
| Manual specification modification | Modified specification remains valid     |
| Ambiguous requirement             | Clarification / explicit uncertainty     |
| Unsupported requirement           | Rejected                                 |
| Invalid vocabulary                | Rejected                                 |
| Invalid relationship              | Rejected                                 |
| Invalid dependency                | Rejected                                 |
| Contradictory constraints         | Rejected by validation                   |
| Invented FORGE property           | Rejected                                 |
| Accepted specification            | Successfully consumed by FORGE           |
