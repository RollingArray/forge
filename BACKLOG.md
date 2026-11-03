# FORGE - Engineering Backlog

## Confirmed implementation gaps

- [ ] GEN-01: Enforce semantic UNIQUE values across generation chunks.
- [ ] GEN-02: Enforce uniqueness when appending values to the semantic store.
- [ ] GEN-03: Validate semantic UNIQUE fields across the complete generated dataset.
- [ ] GEN-04: Include semantic uniqueness in generation quality metrics.

## Potential risks to investigate

- [ ] GEN-05: Handle corrupted or unreadable semantic state safely during recovery.
- [ ] GEN-06: Review atomicity and durability of chunk CSV writes.
- [ ] GEN-07: Review atomicity and recovery of consolidated entity CSV files.

## Pending generation audit

- [ ] Numeric generation and decimal precision/scale.
- [ ] Numeric cross-field business consistency.
- [ ] Semantic format consistency across chunks.
- [ ] Artifact assembly and CSV completeness.
- [ ] Quality metrics and interpretation.
- [ ] Recovery under interruption scenarios.
- [ ] Generation performance and scalability.

## UI acceptance testing

Use a separate data model through the FORGE UI.

Scenario:
- Parent: 125 records (chunks: 50, 50, 25).
- Child: 275 records (chunks: 50, 50, 50, 50, 50, 25).
- Chunk size: 50.

Verify:
- Correct row counts.
- Parent-before-child execution.
- Child references use the complete parent keyspace.
- No dangling foreign keys.
- Final partial chunks are handled correctly.
- Complete CSV artifacts.
- Validation and quality results in the UI.

## Engineering principles

- Specification remains the source of truth.
- Do not change code merely to accommodate the current specification.
- Preserve existing working-tree changes.
- Complete the audit before implementing agreed fixes.
- End-to-end acceptance is through the FORGE UI.


## Numeric generation and validation

- [ ] **NUM-01: Decimal precision and scale**
  Support optional precision and scale in DECIMAL field specifications and enforce them during generation.

- [ ] **NUM-02: Decimal serialization**
  Preserve exact decimal representation throughout generation, persistence, CSV export, and reading. CSV writing currently preserves serialized text.

- [ ] **NUM-03: Decimal validation precision**
  Replace binary float conversion for DECIMAL values with exact decimal handling. Validator constraint and domain comparisons currently use float.

- [ ] **NUM-04: Cross-field numeric constraints**
  Support comparisons between fields, for example BRGEW >= NTGEW. Current constraints compare a field against a constant value.


## Generation recovery and determinism

- [ ] **REC-01: Restore random generator state on resume**
  Resuming an interrupted entity creates fresh seeded random generators but starts directly at the next incomplete chunk. Random streams are not restored or advanced past committed rows. This can repeat random values from earlier chunks and make resumed output differ from uninterrupted output.
  Acceptance: through the FORGE UI, interrupt a multi-chunk generation, resume it, and compare the resulting data with an uninterrupted run using the same specification and seed. Check duplicate values, uniqueness constraints, and output consistency.


- [ ] **NUM-05: Preserve fractional bounds during specification import**
  The import service parses fractional numeric bounds with Decimal but converts them to float before storing them. This can lose precision before generation begins.

- [ ] **QLT-01: Report unexpected categorical values**
  Distribution fidelity counts observed values outside the declared category list in its denominator, but does not explicitly report those unexpected values or their counts. Report unexpected categories separately so domain violations are visible.

- [ ] **QLT-02: Improve numeric statistical reporting**
  Numeric statistics currently convert values to float. A single non-numeric value causes the entire field's statistics to be omitted, without reporting rejected values. Preserve decimal precision and expose valid, invalid, and missing counts.

- [ ] **QLT-03: Make statistical profiling memory-efficient**
  Statistical fidelity currently retains every non-empty value for every field in memory, including non-numeric fields. Use streaming or bounded-memory statistics for large generated datasets.

- [ ] **QLT-04: Make quality status evidence-based**
  The Results summary displays "High Fidelity" whenever a quality profile exists. Derive the status from explicit quality criteria and measured outcomes, or use a neutral label such as "Quality profile available" until such criteria are defined.



- [ ] **QLT-05: Distinguish unavailable metrics from zero**
  The Results summary defaults a missing population fidelity rate to 0%, which can misrepresent unavailable data as a measured zero. Display "Not available" when the metric is absent, consistent with the detailed quality page.



- [ ] **QLT-06: Count distinct categorical identity values**
  Identity-space capacity currently uses the length of a categorical values list. Count distinct values instead, so duplicate configured entries do not inflate the theoretical identity capacity or distort utilization.



## Generation Audit: Remaining Investigations

The following investigations are required to complete the generation-engine audit.
The audit is read-only until findings are consolidated and corrective actions are agreed.
Acceptance testing must be performed through the FORGE UI.

- [ ] **GEN-AUDIT-01: Semantic uniqueness across generation batches**
  Investigate whether semantic UNIQUE values remain unique across chunks and across resumed generation jobs. Inspect semantic value generation, duplicate detection, persistence, refill behavior, and recovery. Establish whether collisions against previously persisted values are detected and handled correctly.
  Acceptance: Generate a multi-chunk dataset with semantic UNIQUE fields through the FORGE UI. Verify uniqueness across the complete output, not just within individual chunks. Include an interrupted and resumed generation scenario.

- [ ] **GEN-AUDIT-02: Population planning and identity-space calculations**
  Review population planning, feasibility calculations, identity-space capacity, and relationship-backed identity dimensions. Examine composite identities, categorical domains, duplicate domain values, multiple parent-backed dimensions, and cases where capacity cannot be determined.
  Acceptance: Use UI-authored specifications with different population sizes and identity configurations. Verify that planning outcomes and reported identity-space measurements are consistent with the specification and generated data.

- [ ] **GEN-AUDIT-03: Artifact integrity and generation recovery**
  Complete the investigation of chunk writing, checkpoint commits, artifact consolidation, checkpoint reconciliation, and interrupted-job recovery. Examine missing, incomplete, duplicated, or uncommitted chunks and the consistency of final CSV artifacts.
  Acceptance: Through the FORGE UI, interrupt and resume a multi-chunk generation. Verify final row counts, chunk completeness, absence of duplicate or missing rows, and consistency between generated files and recorded job results.

- [ ] **GEN-AUDIT-04: Quality measurement completeness and accuracy**
  Complete the review of population fidelity, relationship fidelity, distribution fidelity, statistical fidelity, identity-space utilization, and performance measurements. Examine full-dataset coverage, missing and invalid values, unexpected categories, memory usage, precision, and how unavailable or inconclusive measurements are represented in the UI.
  Acceptance: Compare the quality analysis displayed in FORGE with the actual generated dataset and validation results. Confirm that reported measurements are accurate and that unavailable or inconclusive evidence is not presented as a successful quality outcome.

- [ ] **GEN-AUDIT-05: Generated data consistency and specification compliance**
  Review cross-field consistency, semantic format consistency across chunks, numeric generation, decimal precision, value conversion, and the relationship between configured constraints and generated values. Distinguish implementation defects from capabilities not currently expressed by the specification.
  Acceptance: Create UI-authored specifications containing numeric bounds, categorical values, semantic fields, and applicable constraints. Inspect generated CSV output and validation findings for compliance with the declared specification.

- [ ] **GEN-AUDIT-06: End-to-end generation acceptance**
  Perform one consolidated UI-only acceptance pass after the five investigations are complete and agreed fixes have been implemented. Use a fresh data model with non-multiple chunk sizes to exercise final partial chunks and cross-entity dependencies.
  Suggested scenario:
  - Parent entity: 125 rows, producing chunks of 50, 50, and 25.
  - Child entity: 275 rows, producing chunks of 50, 50, 50, 50, 50, and 25.
  - Child foreign key references the parent identity.
  - Optionally include a grandchild entity referencing the child to exercise multi-level dependency ordering.
  Verify parent-before-child execution, complete parent key availability, valid foreign-key references across all chunks, exact requested row counts, final partial chunks, identity uniqueness, validation results, and complete exported CSV files.
  Do not use alternate-key foreign keys in this scenario because the current specification validation restricts FK targets to declared identity fields.

Audit completion criteria:
- All five investigations have documented findings.
- Confirmed defects are distinguished from specification or product capability gaps.
- Backlog fixes are agreed before implementation begins.
- The consolidated UI acceptance scenario passes.


## Activity Logging Audit

The activity logging review covers backend event recording, event semantics,
persistence reliability, and the Recent Activity presentation.

The following items are based on source-code inspection. Implementation and
acceptance testing remain pending. Preserve the existing activity history and
avoid changing unrelated event behavior.

### Confirmed implementation gaps

- [x] **ACT-01: Introduce a specification-saved activity event**
  Added `SPECIFICATION_SAVED` to the activity taxonomy and presentation
  mapping. The general specification save endpoint now records this event
  after successful persistence, with source attribution (`manual` or `ai`),
  operation, outcome, resulting specification revision, and structural
  counts. The AI authoring workflow explicitly identifies its save as
  AI-originated. CSV imports retain their separate
  `SPECIFICATION_IMPORT_APPLIED` event.
  Acceptance: Verified the AI-generated specification save through the FORGE
  UI and confirmed the event type, source, operation, revision, and counts.

- [ ] **ACT-02: Record whole-specification AI proposal generation**
  Record `AI_PROPOSAL_GENERATED` when the whole-specification proposal endpoint
  successfully generates a proposal. Use `proposal_type="specification"` and
  suitable outcome metadata. Do not record failed provider calls as successful
  proposals.
  Acceptance: Generate a proposal from plain English and tabular input through
  the FORGE UI. Verify the activity entry and its metadata.

- [ ] **ACT-03: Avoid no-op population scaling activities**
  The population scaling update path can persist and record `ENTITY_UPDATED`
  even when the scaling configuration has not changed. Compare the existing
  and requested values before saving. Avoid unnecessary persistence and
  activity records for unchanged values. Capture meaningful before/after
  values in metadata when a change occurs.
  Acceptance: Update population scaling through the FORGE UI. Verify that a
  real change produces one activity entry and an unchanged value produces none.

- [ ] **ACT-09: Enrich specification validation activity metadata**
  The `MODEL_VALIDATED` activity currently records an empty metadata object.
  Inspect the validation result and record useful audit context, including
  validation outcome, finding counts by severity, and the specification
  revision validated, where those values are available. Avoid exposing
  proprietary specification content.
  Acceptance: Validate a specification through the FORGE UI. Verify that the
  activity metadata accurately describes the validation result and revision.

### Specification Wizard activity

- [x] **ACT-08: Record the wizard's Apply additions and open Model Studio action**
  Verify that the wizard action which applies imported additions and saves the
  specification records exactly one `SPECIFICATION_IMPORT_APPLIED` activity.
  The activity must be recorded only after successful specification
  persistence and before navigation to Model Studio. Reuse the existing event
  and import-application recording path where possible. Do not emit a duplicate
  event from both the wizard and the backend service. A failed save must not
  produce a successful activity entry.
  Acceptance: Through the FORGE UI, apply additions and open Model Studio.
  Verify that the saved specification contains the additions and exactly one
  corresponding activity appears in Recent Activity. Repeat with a failed
  save and verify that no successful activity is recorded.

### Release-readiness risks

- [ ] **ACT-04: Make JSON activity persistence concurrency-safe**
  Multiple independently constructed `ActivityService` and
  `JsonActivityRepository` instances write to the same `activities.json` and
  temporary file. Their instance-level locks do not coordinate concurrent
  writes. Atomic replacement alone does not prevent lost updates or temporary
  file collisions.
  Review and agree on a concurrency-safe persistence strategy that preserves
  the repository abstraction and supports the intended deployment model.
  Consider both multiple service instances and multiple application workers.
  Acceptance: Exercise concurrent activity writes and verify that every
  successfully recorded activity is retained, with no corrupted JSON or
  temporary-file collisions.

- [ ] **ACT-05: Review activity metadata exposure**
  Review metadata containing before/after values, configuration details, and
  generation information. Establish which details are appropriate for
  Recent Activity and which should remain operational or restricted data.
  Acceptance: Inspect activity entries through the UI and confirm that
  proprietary specification values and unnecessary sensitive details are
  not exposed.

### Taxonomy and scope decisions

- [ ] **ACT-06: Remove or implement unused data-model duplication activity**
  `DATA_MODEL_DUPLICATED` exists in the activity taxonomy and presentation
  mapping, but no corresponding duplication workflow was found during the
  audit. Confirm product scope. If duplication is not planned, remove the
  unused event and its presentation mapping. If it is planned, implement
  recording after successful duplication.
  Acceptance: The taxonomy and UI accurately reflect supported workflows.

### Deferred capabilities

- [ ] **ACT-07: Revisit generation cancellation activity when cancellation
  is implemented**
  `GENERATION_CANCELLED` exists in the taxonomy and presentation mapping,
  but no user-facing cancellation action or API route was found during the
  audit. Do not implement activity recording without a supported cancellation
  workflow. Revisit this item when cancellation becomes part of the product.
  Acceptance: A successfully cancelled generation job produces one accurate
  cancellation activity entry.

### Confirmed behavior to preserve

- Generation job creation is immediately followed by starting generation
  in the current frontend workflow. Do not introduce a separate
  `GENERATION_JOB_CREATED` event at this stage.
- `GENERATION_STARTED` already captures resumed execution through its
  `resumed` metadata. Do not introduce a separate resume event.
- Entity identity and population changes are represented by `ENTITY_UPDATED`.
  Do not introduce identity-specific event types.
- Generation completion, partial completion, and failure are already recorded.
- Access grant, role change, and revocation events are implemented.
- Foreign-key updates and generation failure recording are implemented.
- Do not infer missing implementation solely from the absence of historical
  records.

### Activity audit acceptance criteria

- Event names and descriptions accurately represent the business outcome.
- Activities are recorded only after the corresponding operation succeeds.
- Failed operations are not presented as successful business outcomes.
- Duplicate or no-op activities are avoided.
- Activity persistence remains reliable under concurrent writes.
- Recent Activity presents useful information without exposing unnecessary
  specification or operational details.
- Existing historical activity records remain readable.
- Final acceptance is performed through the FORGE UI.
