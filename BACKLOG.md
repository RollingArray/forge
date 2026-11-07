# FORGE Engineering Backlog

## 1. Investigations

- [pending] **Generation: Semantic uniqueness**
  Investigate uniqueness across chunks, persisted semantic values, and resumed generation.

- [pending] **Generation: Population planning and identity capacity**
  Review composite identities, categorical domains, relationship-backed identity dimensions, and feasibility calculations.

- [pending] **Implement end-to-end MANY_TO_MANY relationship support**

  Implement logical MANY_TO_MANY relationships using an explicitly defined junction/association entity and its physical foreign-key mappings.

  Scope:
  - Resolve logical relationships to the appropriate junction entity and its two endpoint foreign keys.
  - Validate junction mappings against the identities of both participating entities.
  - Generate valid associations with configurable or deterministic distribution.
  - Enforce mandatory and optional participation on both sides.
  - Prevent duplicate association pairs.
  - Support composite junction identities.
  - Preserve referential integrity across chunks and generation recovery.
  - Validate association cardinality and participation.
  - Include MANY_TO_MANY relationship fidelity in generation quality metrics.

  Acceptance:
  - Every mandatory participating entity instance has at least one association.
  - Every association references existing records on both sides.
  - Duplicate association pairs are rejected.
  - Association distribution satisfies configured requirements.
  - Validation and quality reports measure both endpoints correctly.
  - Tests cover chunk boundaries, composite identities, optional participation, and recovery.


- [pending] **Generation: Artifact integrity and recovery**
  Investigate chunk writes, checkpoint commits, artifact consolidation, reconciliation, and interrupted-job recovery.

  Scope:
  - Verify atomicity and durability of chunk and consolidated CSV writes.
  - Reconcile consolidated artifact row counts with checkpoint committed rows and entity targets.
  - Verify checkpoint and job-progress consistency during startup recovery and resume.
  - Test missing, truncated, uncommitted, and schema-inconsistent chunks.
  - Verify recovery behaviour when checkpoint persistence or artifact consolidation fails.
  - Verify interrupted-entity last-chunk discard and regeneration behaviour.
  - Verify that recovery never exposes incomplete artifacts as valid consolidated output.
  - Verify that quality-analysis failure after full row generation does not misrepresent the generated row count or artifact integrity.

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

### Artifact integrity and recovery

- Chunk CSV files are written directly to their final paths rather than through temporary files and atomic replacement. An interrupted write can leave a truncated chunk.
- Consolidated entity CSV files are also written directly to their final paths. A read or schema failure during consolidation can leave a partial consolidated artifact.
- Consolidation does not compare its actual output row count with the checkpoint's committed row count or the entity target.
- The artifact reader checks committed chunk presence but does not independently establish all recovery invariants, including contiguous chunk numbering, consistent schema, and expected row counts.
- Recovery reconciliation has safeguards for contiguous chunks, missing files, and truncated chunks, but dedicated service-level recovery tests were not found in the inspected test suite.
- Direct test coverage was not found for checkpoint/job-progress divergence, checkpoint save failure, interrupted recovery, or consolidation failure scenarios.
- The recovery policy discards the last committed chunk of an interrupted active entity. Its correctness and expected regeneration behaviour require explicit acceptance testing.

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
- Quality-profile construction runs after validation and can raise an exception that prevents the generation result from being returned.
- Quality analysis has no dedicated test file in the inspected test suite; quality failure and partial-artifact scenarios need explicit coverage.
- Validator sections handle selected conversion and comparison errors, but some malformed values and artifact-reader failures can still escape as exceptions.
- Identity-space capacity can be inflated by duplicate categorical values.

### Activity logging

- Whole-specification AI proposal generation activity gap resolved; successful proposals now create a workspace-level activity entry.


## 3. Features to Implement

- [done] **Record specification save activity**
  Added `SPECIFICATION_SAVED`, source attribution, operation, outcome, revision, and structural counts. Verified AI-originated save through the FORGE UI.

- [done] **Record Specification Wizard CSV import activity**
  Verified `SPECIFICATION_IMPORT_APPLIED` after successful application of CSV additions.

- [done] **Record whole-specification AI proposal generation**
  Added workspace-level `AI_PROPOSAL_GENERATED` activity for successful whole-specification proposals, including proposal outcome, deterministic validation summary, and structural counts. Verified through the FORGE UI alongside the separate AI-sourced `SPECIFICATION_SAVED` event.

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

- [pending] **Make artifact chunk writes atomic**
  Prevent interrupted chunk writes from exposing truncated files at committed artifact paths.

- [pending] **Make consolidated artifact writes atomic**
  Build consolidated CSV output separately and publish it only after successful completion and integrity checks.

- [pending] **Reconcile consolidated artifact row counts**
  Verify consolidated row counts against checkpoint committed rows and entity targets before treating artifacts as usable.

- [pending] **Correct generation failure-state classification**
  Distinguish generation/execution failures from unexpected exceptions during validation execution, quality analysis, artifact finalization, and persistence. Preserve accurate generated-row counts, validation outcomes, and artifact state.

- [pending] **Harden validator exception handling**
  Ensure malformed values and artifact-reading failures are reported consistently without silently terminating validation or misrepresenting validation outcomes.

- [pending] **Test artifact recovery and consolidation failure scenarios**
  Cover missing and truncated committed chunks, uncommitted chunks, schema mismatches, row-count mismatches, checkpoint/job-progress divergence, and checkpoint persistence failures.

- [done] **Support population scaling updates in Entity Edit**
  Enabled editing of FIXED and SCALABLE population modes alongside entity description and population count. Updates record only actual changes with before/after metadata, while unchanged submissions avoid unnecessary persistence and activity records. Verified scaling-only and combined updates through the FORGE UI.


## Engineering Principles

- Specification remains the source of truth.
- Do not change code merely to accommodate the current specification.
- Preserve existing working-tree changes.
- Complete investigations before implementing agreed fixes.
- Distinguish implementation defects from capabilities not yet supported by the specification.
- Perform end-to-end acceptance through the FORGE UI.
