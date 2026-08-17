# Experiment XXX: <Experiment Name>

**Status:** Planned / In Progress / Completed / Failed  
**Experiment Type:** <Foundational / Structural / Statistical / Relationship / Rule / Validation / Performance / etc.>  
**FORGE Area:** <Primary FORGE area>  
**Objective:** <One sentence describing what this experiment is trying to determine.>

---

## 1. Research Question

<The specific question this experiment is attempting to answer.>

---

## 2. Hypothesis

<What we believe will happen and why.>

The hypothesis should be testable.

Where applicable, explicitly state:

- What the generator is expected to achieve
- What assumptions are being made
- What is intentionally not being assumed
- What would cause the hypothesis to be rejected

---

## 3. Scope

This experiment will <brief description of what is being tested>.

### Included

- <Capability>
- <Capability>
- <Capability>
- <Capability>

### Excluded

- <Capability>
- <Capability>
- <Capability>
- <Capability>

These capabilities may be explored in later experiments.

---

## 4. Initial Dataset / Entity

<Describe the dataset or entity used by the experiment.>

The dataset should remain domain-neutral unless the experiment specifically
requires domain-specific behavior.

### Entity

`<ENTITY_NAME>`

### Fields

| Field | Type | Semantic / Behavior |
|---|---|---|
| FIELD_1 | string | <behavior> |
| FIELD_2 | integer | <behavior> |
| FIELD_3 | date | <behavior> |

---

## 5. Experiment Configuration

<Describe the metadata/configuration supplied to the generator.>

Example:

```python
{
    "field": {
        "type": "...",
        "semantic": "...",
        "distribution": "..."
    }
}