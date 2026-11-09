# FORGE Engineering Backlog

This file is the authoritative engineering register for FORGE audit findings,
corrective work, capability development, and end-to-end acceptance.

Status labels:
- [confirmed] Evidence establishes an implementation defect or gap.
- [risk] A plausible reliability or architectural risk requiring a decision or mitigation.
- [test-gap] Required test coverage is missing.
- [decision] Product or specification decision is required.
- [pending] Agreed work that has not yet been implemented or accepted.
- [done] Implemented and verified to the stated acceptance level.
- [active] Currently being implemented; only one work package may be active.
- [agreed] Product or engineering policy explicitly accepted but not yet implemented.

Audit and source-inspection findings do not constitute UI acceptance.
Do not mark an item done based only on source inspection.

---


## Release objective and ordered execution plan

**Destination: FORGE Release Candidate 1.0**

Deliver a stable, specification-driven synthetic data generation platform
whose supported end-to-end workflows are correct, reliable, demonstrable
through the FORGE UI, and ready for controlled release.

### Execution rules

1. Work on exactly one work package at a time.
2. Do not start the next work package until the current package is complete
   and its acceptance criteria have passed.
3. Mark a work package [active] only when work actually begins.
4. Mark individual findings [done] only after implementation, relevant
   automated tests, and the required acceptance evidence are complete.
5. Source inspection and automated tests support acceptance; they do not
   replace the required FORGE UI verification.
6. Preserve existing working-tree changes. Do not overwrite unrelated work.
7. Do not commit or push without explicit approval.
8. If a blocker is discovered, record it and resolve or explicitly agree
   its disposition before proceeding.
9. Do not introduce new capabilities merely to make the specification fit
   the implementation. Agree product and specification decisions first.

Only one work package may be [active] at any time.

### Ordered release work packages

#### WP-01: Specification integrity
Priority: P0
Status: [done]

Scope:
- SPEC-01: Canonical specification validation before generation.
- SPEC-02: Whole-candidate validation before field persistence.
- TEST-09: Specification preflight and candidate validation tests.

Exit criteria:
- [done] Invalid specifications cannot create generation jobs or artifacts.
- [done] Warning-only specifications remain eligible for generation.
- [done] Invalid field changes cannot corrupt an existing valid specification.
- [done] API/service regression tests pass.
- [done] The behavior is verified through the FORGE UI.

Completion evidence:
- Canonical generation preflight and whole-candidate validation are covered
  by the existing specification validation and preflight regression tests.
- Unsupported field types now produce explicit validation errors.
- Constraint diagnostics identify the specific invalid entity, field,
  operator, comparison value or numeric value.
- 73 related regression tests passed.
- Both additional validation fixes were verified through the FORGE UI.

#### WP-02: Generated data correctness
Priority: P0

Scope:
- SEM-01 and SEM-02: Semantic UNIQUE validation and semantic-store integrity.
- POP-01: Correct identity capacity for independent foreign-key dimensions.
- NUM-02, NUM-03 and NUM-05: Exact decimal representation and numeric
  boundary preservation across supported workflows.
- TEST-01 through TEST-04.

Exit criteria:
- Semantic UNIQUE values remain unique across the complete dataset.
- Corrupt semantic state cannot silently cause duplicate generation.
- Population capacity agrees with generation identity construction.
- Supported decimal values and bounds retain their intended precision.
- Relevant regression tests pass.
- The supported behavior is verified through the FORGE UI.

Progress:
- Population allocation solver implementation and regression verification
  completed. See Section 6, Population allocation (WP-02).
- WP-02 remains open for semantic uniqueness, exact decimal handling,
  remaining identity-capacity acceptance, and outstanding test coverage.
- Confirmed allocation diagnostic gap recorded as WP02-POP-002 below.

#### WP-03: Execution, artifacts and recovery
Priority: P0

Scope:
- ART-01 through ART-06: Atomic artifact writes, reconciliation and recovery.
- REC-01: Random generation state and resume determinism.
- SEM-04 and SEM-05: Semantic-store concurrency and recovery robustness.
- TEST-05 and TEST-06.

Exit criteria:
- Interrupted writes cannot expose incomplete final artifacts as valid.
- Checkpoint, progress and artifact row counts reconcile.
- Interrupted generation resumes safely.
- Recovery behavior is deterministic where the specification and seed
  require deterministic equivalence.
- Failure scenarios are covered by automated tests.
- Recovery is demonstrated through the FORGE UI.

#### WP-04: Validation and quality confidence
Priority: P0

Scope:
- GEN-VAL-01: Independent generation and validation outcomes.
- SPEC-03: NOT_EVALUATED reporting semantics.
- QLT-01 through QLT-11: Quality measurement correctness and resilience.
- TEST-10 through TEST-13.

Exit criteria:
- Generation execution status is not incorrectly downgraded by a
  post-generation validation or quality-analysis exception.
- Validation conformance remains independently visible.
- Unsupported or unevaluated rules are never represented as passed.
- Invalid, missing, unavailable and measured-zero quality values are
  distinguishable.
- Quality reporting and frontend/backend calculations agree.
- Automated regression tests pass.
- Results and validation behavior are verified through the FORGE UI.

#### WP-05: Activity and product reliability
Priority: P1

Scope:
- ACT-01 through ACT-06.
- TEST-07, TEST-08 and TEST-14.
- Resolve outstanding activity product decisions where necessary.

Exit criteria:
- Activity persistence and index recovery are reliable.
- Activity access and presentation remain appropriately scoped.
- Supported activity events are recorded consistently.
- Unknown presentation values do not break the activity feed.
- Relevant tests pass and behavior is verified through the FORGE UI.

#### WP-06: Full Release Candidate acceptance
Priority: P1

Scope:
- Execute all applicable scenarios in Section 7.
- Run the full regression suite.
- Review known limitations and deferred capabilities.
- Verify installation, configuration and operational requirements.
- Prepare release notes and RC sign-off evidence.

Exit criteria:
- All P0 work packages are complete.
- P1 work is complete or explicitly accepted as a release limitation.
- P2 work is explicitly deferred or included by an agreed scope decision.
- All supported end-to-end UI scenarios pass.
- No unresolved release-blocking defect remains.
- RC 1.0 is approved for release-candidate use.

### Deferred capability scope

The following work is not automatically part of RC 1.0:
- REL-01: Full logical MANY_TO_MANY relationship support.
- SEM-03: Semantic uniqueness as an additional quality metric.
- NUM-01: Optional DECIMAL precision and scale enhancement.
- NUM-04: Numeric cross-field constraints.

These remain visible in the engineering backlog. They may be promoted into RC scope only through an explicit decision.


## 1. Audit status and agreed decisions

### Completed investigations

- [done] GEN-AUDIT-01: Semantic uniqueness across chunks,
  persisted semantic values and resumed generation.
- [done] GEN-AUDIT-02: Population planning and identity capacity,
  including composite identities and relationship-backed dimensions.
- [done] GEN-AUDIT-03: Artifact integrity and generation recovery.
- [done] GEN-AUDIT-04: Quality measurement completeness and accuracy.
- [done] GEN-AUDIT-05: Specification compliance.
- [done] GEN-AUDIT-06: Semantic uniqueness.
- [done] GEN-AUDIT-07: Population planning and identity capacity.
- [done] GEN-AUDIT-08: MANY_TO_MANY relationship support.
- [done] GEN-AUDIT-09: Activity persistence and concurrency.
- [done] GEN-AUDIT-10: Activity metadata exposure.
- [done] GEN-AUDIT-11: Activity event taxonomy and product coverage.

The above indicate that source investigations have been completed.
They do not indicate that corrective work or end-to-end acceptance has passed.

### Agreed specification and execution policies

- [agreed] Generation preflight:
  Run canonical specification validation before creating a generation job
  or its artifacts. Validation errors block generation. Warnings alone do not.

- [agreed] Independent execution and conformance statuses:
  Generation execution status and validation conformance status are separate.
  A fully generated job may be COMPLETED while conformance is INCOMPLETE or
  NON_CONFORMANT. Validation findings remain visible.

- [agreed] Whole-specification candidate validation:
  Field create/update validates the complete candidate specification before
  persistence.

### Outstanding product and specification decisions

- [decision] Confirm the supported field-type vocabulary, including whether
  DATE is intentionally unsupported.
- [decision] Define which generation parameters must be validated during
  specification authoring and which may be checked at runtime.
- [decision] Define the reporting semantics for NOT_EVALUATED validation rules.
- [decision] Confirm whether data-model duplication is a supported user workflow.
- [decision] Decide whether generation cancellation should be exposed as a
  workspace activity event.
- [decision] Define the intended product contract for logical MANY_TO_MANY
  relationships and junction entities.

---

## 2. Confirmed defects and implementation gaps

### 2.1 Generation execution and validation

- [confirmed] GEN-VAL-01: Post-generation validation exceptions can affect
  the reported generation outcome. A validation failure must not incorrectly
  downgrade an otherwise fully generated job to PARTIALLY_COMPLETED.

  Required behavior:
  - Preserve the actual generation execution outcome.
  - Report validation outcome independently.
  - Keep validation errors and warnings visible.
  - Do not misrepresent generated artifact completeness.

- [done] SPEC-01: Enforce canonical specification validation as a
  generation preflight gate.

  Verified behavior: invalid specifications block generation before job
  creation; warnings alone do not block generation; actionable findings
  are returned.

  Acceptance:
  - Invalid specifications cannot create generation jobs or artifacts.
  - Warnings alone do not block generation.
  - The user receives actionable validation findings.

- [done] SPEC-02: Validate the complete candidate specification before
  field create/update persistence.

  Verified behavior: invalid candidate specifications are rejected and
  existing valid specification state is preserved.

  Acceptance:
  - Invalid candidate specifications are rejected.
  - Existing valid specification state remains unchanged after rejection.

### 2.2 Semantic uniqueness

Existing generation code already performs cross-chunk duplicate checks,
excludes persisted values during semantic refill, and persists generated
semantic values. Do not reintroduce these as wholly missing capabilities.

- [confirmed] SEM-01: Final dataset validation does not independently verify
  fields configured with semantic UNIQUE mode.

  Acceptance:
  - Validate semantic UNIQUE values across the complete generated dataset.
  - Normalize consistently with generation-time duplicate checks.
  - Report violations against the relevant entity and field.

- [confirmed] SEM-02: Corrupt or unreadable semantic JSON is treated as an
  empty semantic store. During recovery, this can cause previously committed
  values to be omitted from duplicate exclusion.

  Acceptance:
  - Do not silently treat corrupted persisted semantic state as valid empty
    state.
  - Fail safely or reconcile against committed artifacts.
  - Preserve the ability to diagnose and recover the affected job.

- [pending] SEM-03: Include semantic uniqueness in quality reporting if the
  quality contract requires it. Keep this separate from correctness validation.

### 2.3 Population planning and identity capacity

- [confirmed] POP-01: Multiple independent identity foreign keys referencing
  the same parent can be deduplicated in population capacity analysis, while
  generation constructs separate identity components. This can understate
  theoretical identity capacity.

  Acceptance:
  - Model independent identity dimensions independently.
  - Ensure planner capacity agrees with the generation identity construction.
  - Cover multiple references to the same parent.

- [pending] POP-02: Align and document the modelling scope of the older
  population capacity analysis and the newer constraint analysis.

  Acceptance:
  - Establish which path is authoritative for each planning operation.
  - Avoid contradictory feasibility results.

### 2.4 Quality analysis and reporting

- [confirmed] QLT-07: Quality-profile construction is not fault-isolated.
  An analysis exception can prevent the generation result from being returned.

  Acceptance:
  - A failure in one quality dimension does not erase valid generation results.
  - The generation execution outcome remains accurate.
  - The failed quality measurement is reported as unavailable or failed,
    not as a successful measurement.
  - Regression tests cover quality-analysis exceptions.

- [confirmed] QLT-01: Unexpected categorical values are not explicitly
  reported with their values and counts.

- [confirmed] QLT-02: A non-numeric value can suppress the entire field's
  numeric statistical profile.

- [confirmed] QLT-03: Statistical profiling retains all non-empty field
  values in memory, creating scalability concerns for large datasets.

- [confirmed] QLT-04: Results summary can display "High Fidelity" whenever
  a quality profile exists, without evidence-based quality criteria.

- [confirmed] QLT-05: Missing quality measurements can be represented as
  zero, confusing unavailable measurements with measured zero values.

- [confirmed] QLT-06: Categorical identity capacity can be inflated when
  duplicate configured categorical values are counted more than once.

- [confirmed] QLT-08: Zero requested rows can produce a population fidelity
  rate of 1.0 without a meaningful population measurement.

- [confirmed] QLT-09: Empty categorical measurements can report a zero
  missing rate, making unavailable evidence indistinguishable from measured zero.

- [confirmed] QLT-10: Frontend entity-level population fidelity uses a
  different calculation from the backend population fidelity calculation.

- [confirmed] QLT-11: Distribution visualization converts null, missing,
  empty and invalid numeric measurements to zero.

  Acceptance across QLT-01 to QLT-06 and QLT-08 to QLT-11:
  - Distinguish valid, invalid, missing and unexpected values.
  - Do not silently omit statistical evidence.
  - Use bounded-memory profiling where practical.
  - Derive quality status from explicit criteria.
  - Represent unavailable metrics as unavailable, not zero.
  - Count distinct categorical values for identity capacity.

---

## 3. Reliability, recovery and robustness risks

### 3.1 Artifact integrity and recovery

- [confirmed] ART-01: Chunk CSV writes are written directly to final paths
  rather than using an atomic replacement strategy.

- [confirmed] ART-02: Consolidated entity CSV writes are not atomic.

- [confirmed] ART-03: Artifact writing does not independently reconcile
  actual output row counts against committed checkpoint counts and targets.

- [risk] ART-04: Artifact reader validation does not independently establish
  every aspect of chunk sequence continuity, row-count consistency and
  schema consistency.

- [test-gap] ART-05: Dedicated generation-service recovery orchestration
  tests are missing.

- [test-gap] ART-06: Recovery tests should cover missing, incomplete,
  duplicated, uncommitted and corrupted artifact/checkpoint combinations,
  checkpoint/job-progress divergence, checkpoint persistence failure,
  consolidation failure and interrupted recovery.

Positive control:
The checkpoint store already uses temporary-file writing, flush, fsync and
atomic replacement. Preserve this behavior.

Acceptance:
- Interrupted writes cannot leave apparently valid partial final artifacts.
- Committed chunk counts reconcile with actual artifact rows.
- Consolidated CSV output is consistent with committed chunks.
- Recovery is deterministic, diagnosable and tested.

### 3.2 Random generation recovery and determinism

- [confirmed] REC-01: Random generator state is not restored or advanced past
  committed rows when resuming an interrupted entity. Resumed output can differ
  from uninterrupted output and can repeat random values from earlier chunks.

  Acceptance:
  - Compare interrupted/resumed output with uninterrupted output using the
    same specification and seed.
  - Verify random fields, uniqueness constraints and final output consistency.
  - Perform acceptance through the FORGE UI.

### 3.3 Semantic store robustness

- [risk] SEM-04: Semantic store read-modify-write operations have no
  demonstrated cross-process locking. Concurrent execution against the same
  job could result in lost updates.

- [test-gap] SEM-05: No dedicated test establishes safe recovery when semantic
  state is corrupted while committed artifacts already exist.

  Acceptance:
  - Establish whether multiple runners can execute the same job concurrently.
  - If concurrency is possible, protect semantic store updates.
  - Test interrupted and resumed semantic generation with real artifacts.

### 3.4 Activity persistence

- [risk] ACT-01: A complete but malformed JSONL activity event can interrupt
  index rebuilding.

- [test-gap] ACT-02: Dedicated activity repository tests are missing for
  persistence, concurrent writers, malformed event recovery and index rebuild.

Positive controls:
- In-process and cross-process locking exist.
- Event appends are flushed and synchronized.
- The event log is authoritative.
- The index can be rebuilt.
- Index replacement uses a temporary file and atomic replacement.

### 3.5 Activity presentation

- [risk] ACT-03: Frontend activity mapping copies backend icon and accent
  values without a demonstrated fallback for unknown values.

- [decision] ACT-04: Review which selected metadata should be rendered in
  user-facing activity descriptions.

### 3.6 Activity event taxonomy

- [decision] ACT-05: Generation cancellation does not currently create a
  workspace activity event. Product decision on whether cancellation should
  be exposed is recorded in the decision section.

- [risk] ACT-06: DATA_MODEL_DUPLICATED has an event type and presentation
  mapping, but no recording call site was identified. Whether duplication is
  a supported workflow remains unverified.

Positive controls:
- Raw metadata is not returned directly by the activity API.
- Data-model activity access is checked.
- Selected metadata is transformed into presentation descriptions.

---

## 4. Specification and capability gaps

### 4.1 Numeric generation and validation

- [pending] NUM-01: Support optional DECIMAL precision and scale in field
  specifications and enforce them during generation.

- [pending] NUM-02: Preserve exact decimal representation through
  specification import, generation, validation, persistence, CSV export
  and reading.

- [pending] NUM-03: Use exact decimal handling for DECIMAL validation rather
  than binary floating-point comparisons.

- [pending] NUM-04: Support numeric cross-field constraints, for example
  BRGEW >= NTGEW, rather than limiting comparisons to constant values.

- [pending] NUM-05: Preserve fractional numeric bounds during specification
  import without converting exact Decimal values to float.

### 4.2 MANY_TO_MANY relationship support

- [pending] REL-01: Implement end-to-end logical MANY_TO_MANY relationship
  support using an explicitly defined junction/association entity and its
  physical foreign-key mappings.

  Scope:
  - Resolve logical relationships to the appropriate junction entity and
    its two endpoint foreign keys.
  - Validate junction mappings against identities of both participating
    entities.
  - Generate valid associations with configurable or deterministic
    distribution.
  - Enforce mandatory and optional participation on both sides.
  - Prevent duplicate association pairs.
  - Support composite junction identities.
  - Preserve referential integrity across chunks and generation recovery.
  - Validate association cardinality and participation.
  - Include MANY_TO_MANY relationship fidelity in generation quality metrics.

  Current capability:
  - Direct logical MANY_TO_MANY declarations are unsupported.
  - A junction entity with two ordinary foreign keys can be represented.
  - FORGE does not yet interpret those foreign keys as a combined logical
    association with endpoint cardinality and participation semantics.
  - Unsupported relationship rules may remain NOT_EVALUATED.

  Acceptance:
  - Every mandatory participating entity instance has at least one
    association.
  - Every association references existing records on both sides.
  - Duplicate association pairs are rejected.
  - Association distribution satisfies configured requirements.
  - Validation and quality reports measure both endpoints correctly.
  - Tests cover chunk boundaries, composite identities, optional
    participation and recovery.

### 4.3 Validation semantics

- [confirmed] REL-02: Unsupported or unmapped relationship rules can remain
  NOT_EVALUATED. They must not be presented as successfully validated.

  Acceptance:
  - Unsupported relationship rules remain explicitly identifiable.
  - NOT_EVALUATED findings are visible in validation results.
  - Overall conformance remains INCOMPLETE when required rules are
    not evaluated.

- [pending] SPEC-03: Define and implement explicit reporting semantics for
  NOT_EVALUATED rules, including the difference between incomplete evidence
  and successful conformance.

- [decision] SPEC-04: Confirm whether DATE should be added to the supported
  field vocabulary. Do not add DATE support without an explicit decision.

- [decision] SPEC-05: Define the authoring-time versus runtime validation
  contract for generation parameters.

---

## 5. Test gaps

- [test-gap] TEST-01: Add semantic store corruption and resume tests.
- [test-gap] TEST-02: Add final dataset semantic UNIQUE validation tests.
- [test-gap] TEST-03: Add population analyzer tests for categorical and
  bounded integer identity capacity.
- [test-gap] TEST-04: Add population analyzer tests for multiple independent
  foreign-key identity dimensions referencing the same parent.
- [test-gap] TEST-05: Add generation-service recovery orchestration tests.
- [test-gap] TEST-06: Add artifact row-count and schema reconciliation tests.
- [test-gap] TEST-07: Add activity repository persistence and concurrency tests.
- [test-gap] TEST-08: Add activity index recovery tests for malformed complete
  JSONL records.
- [done] TEST-09: Specification preflight and whole-candidate validation
  regression coverage is in place and passed as part of the 73-test
  WP-01-related regression run.
- [test-gap] TEST-10: Add validator tests for nulls, malformed typed values,
  domain bounds, artifact-reader failures and NOT_EVALUATED semantics.
  Verify that validator exceptions do not silently terminate validation or
  misrepresent conformance.
- [test-gap] TEST-11: Add regression tests for GEN-VAL-01, ensuring
  post-generation validation exceptions do not misclassify completed generation.
- [test-gap] TEST-12: Add end-to-end MANY_TO_MANY tests when that capability
  is implemented.
- [test-gap] TEST-13: Add quality reporting regression tests for zero-target
  populations, empty categorical measurements, backend/frontend fidelity
  agreement, invalid distribution measurements, invalid numeric values,
  unexpected categorical values, unavailable versus measured-zero values,
  bounded-memory profiling and isolated quality-analysis failures.
- [test-gap] TEST-14: Add activity taxonomy tests for cancellation and
  duplication recording once the corresponding product decisions are made.

Existing coverage must be reused. Do not add duplicate tests merely to repeat
behavior already adequately tested.

---

## 6. Completed work

### Specification validation (WP-01)

- [done] WP01-VAL-001: Detect unsupported field types.
  Unsupported field types now produce an explicit Entity validation error
  identifying the field, unsupported type and supported vocabulary.
  Verified through the FORGE UI.

- [done] WP01-DIAG-001: Improve constraint diagnostic precision.
  Constraint findings now distinguish missing or unknown entities and
  fields, unsupported operators, missing comparison values and invalid
  numeric values. Verified through the FORGE UI.

### Activity logging

- [done] Record specification save activity.
  Added SPECIFICATION_SAVED, source attribution, operation, outcome, revision
  and structural counts. AI-originated save was verified through the FORGE UI.

- [done] Record Specification Wizard CSV import activity.
  SPECIFICATION_IMPORT_APPLIED was verified after successful application of
  CSV additions.

- [done] Record whole-specification AI proposal generation.
  Added workspace-level AI_PROPOSAL_GENERATED activity for successful
  whole-specification proposals, including proposal outcome, deterministic
  validation summary and structural counts. Verified through the FORGE UI.

- [done] Enrich specification validation activity.
  Added outcome, specification revision, continuation status,
  error/warning/passed counts, total checks and validated entity count to
  MODEL_VALIDATED and MODEL_VALIDATION_FAILED activity metadata.
  Successful validation was verified through the FORGE UI.

### Entity population editing

- [done] Support population scaling updates in Entity Edit.
  Enabled editing of FIXED and SCALABLE population modes alongside entity
  description and population count. Updates record only actual changes with
  before/after metadata. Verified scaling-only and combined updates through
  the FORGE UI.

### Generation semantic uniqueness

- [done] Enforce semantic UNIQUE values across generation chunks and
  persisted semantic batches.
  Existing implementation checks within-batch and persisted-value collisions,
  refills missing values and persists semantic values. Existing tests cover
  cross-chunk uniqueness and resume behavior.
  This does not close SEM-01 or SEM-02.

### Population allocation (WP-02)

- [done] WP02-POP-001: Implement bounded, constraint-aware integer
  population target allocation.

  Replaced the previous allocation approach with a bounded integer solver
  that supports coordinated allocation across entities while respecting
  the supported population, relationship and identity constraints.

  Verified solver behavior:
  - Preserve FIXED entity populations.
  - Respect minimum and maximum population bounds.
  - Enforce mandatory parent participation.
  - Respect identity capacity constraints.
  - Preserve independent identity dimensions, including repeated references
    to the same parent.
  - Produce an exact requested total for FEASIBLE allocations.
  - Distinguish FEASIBLE, INFEASIBLE and UNRESOLVED outcomes.
  - Produce deterministic allocations for identical inputs.
  - Independently verify the resulting allocation against its constraints.

  Automated verification:
  - 37 focused solver and integration tests passed.
  - 4 bounded solver contract tests passed.
  - 51 population regression tests passed.
  - Enterprise model with 40 entities, 52 relationships, 52 foreign keys,
    62 population constraints and 40 identity capacity definitions passed
    independent constraint verification.
  - Exact target totals and deterministic results verified for
    100,000, 1,000,000 and 5,000,000 records.

  FORGE UI verification:
  - 40-entity enterprise model: 5,000,000 requested and candidate records,
    zero gap, 40/40 entities feasible.
  - 15-entity model: 1,000,000 requested and candidate records,
    zero gap, 15/15 entities feasible.
  - FIXED BUSINESS_UNIT population remained 4 in both scenarios.

  Remaining verification:
  - Dedicated finite maximum-capacity scenario.
  - Explicit allocator handling of unsupported relationship semantics.
  - UI driver selection currently defaults silently to the first entity.
  - Review the Minimum Allowed label because displayed minimums can be
    candidate-dependent.

  This implementation does not by itself close all WP-02 acceptance
  criteria or the separate semantic and decimal work items.

- [open] WP02-POP-002: Surface allocation support diagnostics and
  distinguish unsupported semantics from target infeasibility.

  Confirmed behavior:
  - The allocator blocks unsupported relationship and identity semantics
    by returning UNRESOLVED before allocation.
  - The backend response already includes allocation_status and
    allocation_diagnostics.
  - Unsupported identity configurations with structural ERROR diagnostics
    are returned through the structural validation gate.
  - Unsupported relationship semantics are returned through the allocation
    support gate with relationship-specific reasons.
  - The frontend candidate model and decision UI previously did not expose
    these response fields or distinguish the failure categories.
  - The candidate decision UI now distinguishes FEASIBLE, INFEASIBLE,
    UNRESOLVED, and a solver-feasible candidate that fails overall
    population feasibility.

  Acceptance criteria:
  - Expose allocation status and diagnostics in the frontend model.
  - Add backend regression tests for unsupported identity and relationship
    diagnostic paths.
  - Distinguish INFEASIBLE from UNRESOLVED in the UI.
  - Preserve the overall feasible check when presenting success.
  - Display corrective guidance appropriate to the actual failure.
  - Verify unsupported relationship and identity scenarios through
    the FORGE UI.

  This is a diagnostic and user experience gap. The existing support gate
  prevents these unsupported scenarios from being reported as FEASIBLE.
  No solver correctness defect has been established by this finding.

---

## 7. End-to-end FORGE UI acceptance

Acceptance must be performed through the FORGE UI.
Source inspection and automated tests are supporting evidence, not UI
acceptance proof.

### 7.1 Core generation scenario

Use a fresh data model.

Scenario:
- Parent entity: 125 rows, chunks of 50, 50 and 25.
- Child entity: 275 rows, chunks of 50, 50, 50, 50, 50 and 25.
- Child foreign key references the parent identity.
- Optionally include a grandchild entity referencing the child.
- Use a chunk size of 50.
- Do not use alternate-key foreign keys in this scenario because current
  specification validation restricts FK targets to declared identity fields.

Verify:
- Parent-before-child execution.
- Complete parent key availability.
- Valid foreign-key references across all chunks.
- Exact requested row counts.
- Correct final partial chunks.
- Identity uniqueness.
- Validation results and conformance status.
- Quality metrics and unavailable metric presentation.
- Complete exported CSV files.
- Results UI agrees with actual generated data.

### 7.2 Semantic uniqueness scenario

- Include a semantic UNIQUE field.
- Generate multiple chunks.
- Verify uniqueness across the complete output.
- Interrupt and resume generation.
- Verify persisted semantic state and final uniqueness.

### 7.3 Recovery scenario

- Interrupt a multi-chunk generation.
- Resume through the UI.
- Verify checkpoint reconciliation, chunk completeness, row counts and
  final artifact consistency.
- Compare with an uninterrupted run using the same specification and seed
  where deterministic equivalence is expected.

### 7.4 Specification and validation scenario

- Exercise invalid and warning-only specifications.
- Verify invalid specifications are blocked before job creation.
- Verify warning-only specifications remain eligible for generation.
- Verify execution status remains separate from conformance status.
- Verify NOT_EVALUATED findings are not presented as successful checks.

### 7.5 Activity scenario

- Verify generation start and terminal activity events.
- Verify cancellation activity behavior once its product decision is made.
- Verify actor, target and data-model descriptions.
- Verify no raw metadata or internal identifiers are exposed.
- Verify unknown presentation values do not break the activity feed.

### 7.6 MANY_TO_MANY scenario

Pending implementation and product contract.
Verify both endpoints, mandatory/optional participation, duplicate association
prevention, composite identities, chunk boundaries, recovery and quality
reporting.

---

## 8. Engineering principles

- Specification remains the source of truth.
- Do not change code merely to accommodate the current specification.
- Preserve existing working-tree changes.
- Complete investigations before implementing agreed fixes.
- Distinguish implementation defects from capabilities not yet supported by
  the specification.
- Do not silently convert unavailable evidence into successful outcomes.
- Preserve independent generation and validation statuses.
- Reuse existing tests and avoid duplicate coverage.
- Perform end-to-end acceptance through the FORGE UI.
- Do not commit or push without explicit approval.
