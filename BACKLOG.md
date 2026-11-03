# FORGE Engineering Backlog

## 1. Investigations

- [pending] **Generation: Semantic uniqueness**
  Investigate uniqueness across chunks, persisted semantic values, and resumed generation.

- [pending] **Generation: Population planning and identity capacity**
  Review composite identities, categorical domains, relationship-backed identity dimensions, and feasibility calculations.

- [pending] **Generation: Artifact integrity and recovery**
  Investigate chunk writes, checkpoint commits, artifact consolidation, reconciliation, and interrupted-job recovery.

- [pending] **Generation: Quality measurement**
  Review population, relationship, distribution, statistical fidelity, identity-space utilization, and performance measurements.

- [pending] **Generation: Specification compliance**
  Review numeric generation, decimal precision, cross-field consistency, semantic formats, value conversion, and constraint enforcement.

- [pending] **Generation: End-to-end UI acceptance**
  Complete a consolidated acceptance run after agreed fixes are implemented.

  Suggested scenario:
  - Parent: 125 rows, chunks of 50, 50, and 25.
  - Child: 275 rows, chunks of 50, 50, 50, 50, 50, and 25.
  - Child foreign key references the parent identity.
  - Optionally include a grandchild referencing the child.

  Verify execution order, complete parent key availability, referential integrity, exact row counts, partial chunks, identity uniqueness, validation, quality results, and complete CSV artifacts.

- [pending] **Activity: Persistence concurrency**
  Investigate concurrent writes from multiple activity service instances and application workers.

- [pending] **Activity: Metadata exposure**
  Review which activity metadata is appropriate for Recent Activity and which should remain operational or restricted.

- [pending] **Activity: Event taxonomy and product scope**
  Confirm whether data-model duplication and generation cancellation are supported workflows.


## 2. Found Gaps

### Generation and semantic data

- Semantic UNIQUE values are not comprehensively enforced across generation chunks and the complete dataset.
- Semantic value persistence and recovery need stronger duplicate handling.
- Random generator state is not restored when resuming an interrupted entity, which can cause resumed output to differ from uninterrupted output.
- Chunk writing and consolidated CSV artifact recovery require further reliability review.

### Numeric generation and validation

- DECIMAL specifications do not fully support precision and scale.
- Numeric validation uses binary floating-point conversion for DECIMAL values.
- Numeric cross-field comparisons, such as `BRGEW >= NTGEW`, are not currently supported.
- Specification import converts fractional numeric bounds to float, potentially losing precision.

### Quality analysis

- Unexpected categorical values are not explicitly reported.
- Numeric statistical reporting can omit an entire field when invalid values are encountered.
- Statistical profiling retains all field values in memory.
- Quality status can display High Fidelity without evidence-based criteria.
- Missing population fidelity measurements can be displayed as zero.
- Identity-space capacity can be inflated by duplicate categorical values.

### Activity logging

- Whole-specification AI proposal generation needs a dedicated activity entry.
- Population scaling updates can generate activity records for unchanged values.
- Specification validation activity currently lacks useful metadata.


## 3. Features to Implement

- [done] **Record specification save activity**
  Added `SPECIFICATION_SAVED`, source attribution, operation, outcome, revision, and structural counts. Verified AI-originated save through the FORGE UI.

- [done] **Record Specification Wizard CSV import activity**
  Verified `SPECIFICATION_IMPORT_APPLIED` after successful application of CSV additions.

- [pending] **Record whole-specification AI proposal generation**
  Record successful AI proposal generation with suitable proposal type and outcome metadata.

- [done] **Enrich specification validation activity**
  Added outcome, specification revision, continuation status, error/warning/passed counts, total checks, and validated entity count to `MODEL_VALIDATED` and `MODEL_VALIDATION_FAILED` activity metadata. Successful validation was verified through the FORGE UI, including reconciliation of all 17 findings.

- [pending] **Support DECIMAL precision and scale**
  Add optional precision and scale to DECIMAL field specifications and enforce them during generation.

- [pending] **Support numeric cross-field constraints**
  Enable comparisons between fields rather than only comparisons against constant values.

- [pending] **Improve quality reporting**
  Report unexpected categories, distinguish invalid and missing values, and establish evidence-based quality status.

- [pending] **Improve statistical profiling**
  Support bounded-memory profiling for large generated datasets.

- [pending] **Improve identity-space calculations**
  Count distinct categorical values when calculating identity capacity.


## 4. Bugs to Resolve

- [pending] **Enforce semantic uniqueness across chunks**
  Prevent duplicate semantic UNIQUE values across the complete generated dataset.

- [pending] **Enforce uniqueness in semantic storage**
  Detect and reject duplicate values when appending to the semantic store.

- [pending] **Validate semantic uniqueness after generation**
  Check semantic UNIQUE fields across the complete generated dataset.

- [pending] **Include semantic uniqueness in quality metrics**
  Make uniqueness violations visible in generation quality results.

- [pending] **Preserve random generator state on resume**
  Restore or correctly advance random streams when resuming interrupted generation.

- [pending] **Preserve exact decimal representation**
  Avoid precision loss during specification import, generation, validation, persistence, and CSV processing.

- [pending] **Report invalid numeric values**
  Prevent invalid values from silently suppressing an entire field's statistical results.

- [pending] **Report unavailable quality metrics correctly**
  Do not represent missing measurements as zero or report High Fidelity without supporting evidence.

- [pending] **Avoid no-op population scaling activities**
  Do not persist or record an update when the requested scaling configuration is unchanged.


## Engineering Principles

- Specification remains the source of truth.
- Do not change code merely to accommodate the current specification.
- Preserve existing working-tree changes.
- Complete investigations before implementing agreed fixes.
- Distinguish implementation defects from capabilities not yet supported by the specification.
- Perform end-to-end acceptance through the FORGE UI.
