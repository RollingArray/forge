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
Status: [active]

Scope:
- SEM-01 and SEM-02: Semantic UNIQUE validation and semantic-store integrity.
- POP-01: Correct identity capacity for independent foreign-key dimensions.
- NUM-01: Optional DECIMAL precision and scale authoring, validation and
  generation.
- NUM-02, NUM-03 and NUM-05: Exact decimal representation and numeric
  boundary preservation across supported workflows.
- TEST-01 through TEST-04.

Exit criteria:
- [done] Semantic UNIQUE values remain unique across the complete dataset.
- [done] Corrupt semantic state cannot silently cause duplicate generation.
- [done] Population capacity agrees with generation identity construction.
- [done] Supported decimal values and bounds retain their intended precision.
- [done] Focused exact-decimal backend and frontend regression tests pass.
- [done] Remaining semantic and identity-capacity backend regression tests pass.
- [pending] Supported behavior is verified through the FORGE UI.

Completion evidence:
- Population allocation solver implementation and regression verification
  completed. See Section 6, Population allocation (WP-02).
- WP02-POP-002 frontend implementation completed. Allocation status and
  diagnostics are exposed, and the candidate decision UI distinguishes
  FEASIBLE, INFEASIBLE and UNRESOLVED outcomes.
- SEM-01: Semantic UNIQUE evaluation errors now fail overall validation
  rather than allowing a fail-open result. Commit `c98810e`.
- SEM-02: Missing UNIQUE semantic state is reconstructed from committed
  artifacts only after validating completeness and uniqueness. Invalid
  artifacts and corrupt existing semantic state fail closed. Commit
  `6ad7c32`.
- 14 validator tests passed for SEM-01; 103 generation service tests
  passed for SEM-02, including six real-artifact resume scenarios.
- 78 focused population and generation regression tests passed,
  including finite local identity candidate-capacity rejection.
- Exact DECIMAL implementation completed across the covered backend and
  frontend paths.
- NUM-01: Optional DECIMAL precision and scale implemented across backend
  validation, exact scaled-integer generation, and frontend field authoring.
  Supports UNIFORM and NORMAL distributions while preserving legacy
  behavior when precision and scale are omitted.
- NUM-01 frontend supports precision/scale validation, editing, AI proposal
  restoration, serialization and reset behavior.
- 172 focused backend regression tests passed for decimal precision,
  field-generation validation and generation services.
- Full backend API suite: 386 tests passed.
- Angular production build passed. Frontend unit tests: 8 passed and 1
  failed in the app scaffold title assertion (`app.spec.ts`); its status
  before this change has not been established.
- NUM-01 FORGE UI acceptance remains outstanding.
- 168 focused backend pytest tests passed, covering decimal import,
  validation, conversion, planning, persistence, checkpoint hashing and
  exact constraint comparison.
- 7 exact-decimal frontend utility tests passed.
- Angular production build completed successfully.
- Playwright acceptance remains outstanding for decimal field authoring,
  constraint authoring, persistence, generation and CSV output.
- SEM-01 and SEM-02 implementation and regression verification completed.
  Remaining identity-capacity diagnostic acceptance is tracked under POP-01.
- TEST-01 through TEST-04 require review and completion.

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

#### WP-06: Model Studio E2E test implementation
Priority: P0
Status: [active]

Objective:
- Implement and execute the finalized FORGE Model Studio E2E Test Catalogue.
- Complete all 28 suites, MS01–MS28, one suite at a time.
- Use Aerospace Enterprise Model v2 as the primary integrated test model.

Execution standards:
- Playwright for frontend end-to-end tests.
- Pytest for backend regression tests.
- Angular production build for frontend build validation.
- Do not add Angular unit or component tests.
- Agree the test architecture, fixtures, setup and cleanup strategy before implementation.
- Preserve the approved suite IDs, case IDs, scenarios and expected outcomes.
- Update each case from [pending] to [active] when work begins and [done] only after execution and required evidence pass.
- Record relevant test evidence and commit references as work is completed.

Suite and test-case tracking:

##### MS01: Model Studio entry and navigation
Status: [done]
Objective: Verify that a user can enter Model Studio and navigate the model authoring experience.
- [done] **MS01-01**: Open Model Studio for a valid data model. Expected result: Model Studio loads successfully.
- [done] **MS01-02**: Load an existing specification. Expected result: Entities and relationships appear.
- [done] **MS01-03**: Open a model with no entities. Expected result: Empty state is displayed correctly.
- [done] **MS01-04**: Navigate between Model Studio and validation. Expected result: Navigation retains the correct data model context.
- [done] **MS01-05**: Open an invalid or unavailable model. Expected result: Appropriate error state is displayed.
- [done] **MS01-06**: Reload Model Studio. Expected result: Specification is loaded again from persisted state.

Evidence:
- All six MS01 Playwright E2E cases passed.
- Full local Playwright regression: 59 passed, 0 failed.
- Angular production build passed.

##### MS02: Entity creation
Status: [done]
Objective: Verify entity creation, configuration, validation and persistence.
- [done] **MS02-01**: Open the create-entity dialog. Expected result: Dialog opens with the required controls.
- [done] **MS02-02**: Create entity with valid name and description. Expected result: Entity is created with default population settings.
- [done] **MS02-03**: Create entity with custom population settings. Expected result: Configured population and scaling are persisted.
- [done] **MS02-04**: Prevent entity creation when required name is missing. Expected result: Save is blocked.
- [done] **MS02-05**: Reject duplicate entity name. Expected result: Duplicate is rejected.
- [done] **MS02-06**: Cancel entity creation. Expected result: No entity is persisted.
- [done] **MS02-07**: Verify entity persistence after reload. Expected result: Entity details remain available after reload.

Evidence:
- All seven MS02 Playwright E2E cases passed.
- Complete MS02 run: 8 passed, 0 failed, including local authentication setup.
- Verified HTTP 201 creation responses, default and custom population configuration, validation, duplicate rejection, cancellation and persistence after reload.
- Commit: fe19966 (test(e2e): complete Model Studio entity creation coverage).

##### MS03: Entity editing
Status: [done]
Objective: Verify modification of an existing entity.
- [done] **MS03-01**: Open an existing entity for editing. Expected result: Existing values populate the dialog.
- [done] **MS03-02**: Update entity description. Expected result: Updated description is persisted.
- [done] **MS03-03**: Update population. Expected result: Updated population is persisted.
- [done] **MS03-04**: Attempt invalid entity update. Expected result: Validation prevents invalid save.
- [done] **MS03-05**: Cancel editing. Expected result: Original values remain unchanged.
- [done] **MS03-06**: Reload after editing. Expected result: Updated entity values are displayed.

Evidence:
- All six MS03 Playwright E2E cases passed.
- Complete MS03 run: 7 passed, 0 failed, including local authentication setup.
- Verified existing entity values, description and population updates, invalid population validation, cancellation without an update request, and persistence after browser reload.

##### MS04: Entity deletion
Status: [done]
Objective: Verify safe entity deletion and dependency handling.
- [done] **MS04-01**: Request entity deletion. Expected result: Confirmation is displayed.
- [done] **MS04-02**: Cancel deletion. Expected result: Entity remains.
- [done] **MS04-03**: Confirm deletion of an eligible entity. Expected result: Entity is deleted.
- [done] **MS04-04**: Attempt deletion with dependent fields or model structures. Expected result: Dependency rules are enforced.
- [done] **MS04-05**: Simulate deletion API failure. Expected result: Error is displayed and state is retained.
- [done] **MS04-06**: Retry deletion after failure. Expected result: Deletion can complete successfully.

Evidence:
- All six MS04 Playwright E2E cases passed.
- Complete MS04 run: 7 passed, 0 failed, including local authentication setup.
- Verified deletion confirmation, cancellation without deletion, successful HTTP 204 deletion, HTTP 409 dependency protection, HTTP 500 failure handling with retained state, and successful retry after failure.
- No application code changes were required.

##### MS05: Field creation
Status: [pending]
Objective: Verify adding fields to an entity.
- [pending] **MS05-01**: Open field creation dialog. Expected result: Dialog opens in create mode.
- [pending] **MS05-02**: Create a valid field. Expected result: Field is created.
- [pending] **MS05-03**: Create field with empty name. Expected result: Save is blocked.
- [pending] **MS05-04**: Create duplicate field name. Expected result: Duplicate is rejected.
- [pending] **MS05-05**: Cancel field creation. Expected result: No field is persisted.
- [pending] **MS05-06**: Reload after creation. Expected result: Field appears in the entity.

##### MS06: Field editing
Status: [pending]
Objective: Verify field modification while preserving existing configuration.
- [pending] **MS06-01**: Open existing field. Expected result: Existing configuration is populated.
- [pending] **MS06-02**: Edit permitted field properties. Expected result: Changes are saved.
- [pending] **MS06-03**: Verify locked configuration options. Expected result: Restricted options cannot be changed.
- [pending] **MS06-04**: Cancel field editing. Expected result: Original configuration remains.
- [pending] **MS06-05**: Reload after editing. Expected result: Saved field configuration is retained.

##### MS07: Field deletion
Status: [pending]
Objective: Verify safe field deletion.
- [pending] **MS07-01**: Request field deletion. Expected result: Confirmation is displayed.
- [pending] **MS07-02**: Cancel deletion. Expected result: Field remains.
- [pending] **MS07-03**: Delete field without dependencies. Expected result: Field is removed.
- [pending] **MS07-04**: Delete field used by identity. Expected result: Deletion is blocked.
- [pending] **MS07-05**: Delete field used by FK, relationship or constraint. Expected result: Dependency rules are enforced.
- [pending] **MS07-06**: Simulate deletion failure and retry. Expected result: Error is displayed and retry works.

##### MS08: Field type and generation configuration
Status: [pending]
Objective: Verify all supported field types and their configuration options.
- [pending] **MS08-01**: Create IDENTIFIER field. Expected result: Sequential identity values.
- [pending] **MS08-02**: Create STRING with RANDOM_STRING. Expected result: Values respect configured length.
- [pending] **MS08-03**: RANDOM_STRING with ALPHA. Expected result: Alphabetic characters only.
- [pending] **MS08-04**: RANDOM_STRING with DIGITS. Expected result: Numeric characters only.
- [pending] **MS08-05**: RANDOM_STRING with ALPHANUMERIC. Expected result: Only permitted characters.
- [pending] **MS08-06**: Configure minimum and maximum string length. Expected result: Generated lengths stay within range.
- [pending] **MS08-07**: Configure STRING with PATTERN. Expected result: Generated values follow pattern tokens.
- [pending] **MS08-08**: Pattern containing literal characters. Expected result: Literal characters are preserved.
- [pending] **MS08-09**: Configure STRING with SEMANTIC / UNIQUE. Expected result: Each requested row receives its corresponding unique semantic value.
- [pending] **MS08-10**: Configure STRING with SEMANTIC / VOCABULARY. Expected result: Generated values come from semantic vocabulary.
- [pending] **MS08-11**: Configure INTEGER with UNIFORM. Expected result: Whole-number values remain within bounds.
- [pending] **MS08-12**: Configure INTEGER with DISCRETE_UNIFORM. Expected result: Whole-number values remain within bounds.
- [pending] **MS08-13**: Configure DECIMAL with UNIFORM. Expected result: Decimal values remain within bounds.
- [pending] **MS08-14**: Configure DECIMAL with NORMAL. Expected result: Bounded normal values are produced.
- [pending] **MS08-15**: Configure DECIMAL with precision and scale. Expected result: Values respect configured decimal grid.
- [pending] **MS08-16**: Configure DECIMAL without precision and scale. Expected result: Valid bounded decimal values are produced.
- [pending] **MS08-17**: Configure BOOLEAN. Expected result: Valid boolean values are produced.
- [pending] **MS08-18**: Configure CATEGORICAL. Expected result: Values belong to the configured set.
- [pending] **MS08-19**: Save and reload each field type. Expected result: Configuration remains intact.
- [pending] **MS08-20**: Enter invalid configuration parameters. Expected result: UI prevents invalid save.
- [pending] **MS08-21**: Submit unsupported generation configuration through API. Expected result: Backend rejects unsupported configuration.

##### MS09: Identity and primary keys
Status: [pending]
Objective: Verify single-field identity creation and integrity.
- [pending] **MS09-01**: Open identity dialog. Expected result: Existing identity state is displayed.
- [pending] **MS09-02**: Select one field as identity. Expected result: Field is selected.
- [pending] **MS09-03**: Save identity. Expected result: Identity is persisted.
- [pending] **MS09-04**: Attempt empty identity. Expected result: Save is blocked.
- [pending] **MS09-05**: Attempt identity with undefined field. Expected result: Backend rejects it.
- [pending] **MS09-06**: Attempt duplicate identity field. Expected result: Duplicate is rejected.
- [pending] **MS09-07**: Use IDENTIFIER field without SEQUENTIAL_ID. Expected result: Validation rejects configuration.
- [pending] **MS09-08**: Use valid sequential identifier. Expected result: Identity configuration is accepted.
- [pending] **MS09-09**: Verify generated identity values. Expected result: Values are unique and non-null.
- [pending] **MS09-10**: Edit existing identity. Expected result: Updated identity is persisted.
- [pending] **MS09-11**: Cancel identity changes. Expected result: Original identity remains.
- [pending] **MS09-12**: Reload specification. Expected result: Identity is preserved.
- [pending] **MS09-13**: Generate multiple records. Expected result: Identity uniqueness holds across generated rows.
- [pending] **MS09-14**: Validate identity with missing or null values. Expected result: Integrity validation reports failure.

##### MS10: Composite identity keys
Status: [pending]
Objective: Verify multi-field identity definitions and ordering.
- [pending] **MS10-01**: Open identity dialog with existing composite key. Expected result: All identity fields are selected.
- [pending] **MS10-02**: Select multiple fields. Expected result: Multiple fields can be selected.
- [pending] **MS10-03**: Save composite identity. Expected result: Ordered field list is persisted.
- [pending] **MS10-04**: Attempt duplicate component. Expected result: Duplicate is rejected.
- [pending] **MS10-05**: Attempt undefined component. Expected result: Validation rejects it.
- [pending] **MS10-06**: Edit composite identity. Expected result: Updated components are persisted.
- [pending] **MS10-07**: Cancel composite identity edit. Expected result: Original composite key remains.
- [pending] **MS10-08**: Generate data using composite identity. Expected result: Combined values uniquely identify rows.
- [pending] **MS10-09**: Verify duplicate composite key detection. Expected result: Validator reports duplicate identity.
- [pending] **MS10-10**: Reload specification. Expected result: Component ordering is preserved.

##### MS11: Foreign keys
Status: [pending]
Objective: Verify single-field FK creation and integrity.
- [pending] **MS11-01**: Open FK dialog. Expected result: Dialog opens.
- [pending] **MS11-02**: Select source entity. Expected result: Source is correctly identified.
- [pending] **MS11-03**: Select target entity. Expected result: Target is correctly identified.
- [pending] **MS11-04**: Attempt same source and target. Expected result: Invalid self-reference is prevented.
- [pending] **MS11-05**: Select target without identity. Expected result: FK cannot be saved.
- [pending] **MS11-06**: Resolve matching source and target fields. Expected result: Mapping is derived correctly.
- [pending] **MS11-07**: Source field missing. Expected result: Save is blocked.
- [pending] **MS11-08**: Create valid FK. Expected result: FK is persisted.
- [pending] **MS11-09**: Attempt duplicate FK. Expected result: Duplicate is rejected.
- [pending] **MS11-10**: Edit FK. Expected result: Mapping remains valid.
- [pending] **MS11-11**: Cancel FK edit. Expected result: Original FK remains.
- [pending] **MS11-12**: Delete FK with no relationship dependency. Expected result: FK is deleted.
- [pending] **MS11-13**: Delete FK with dependent relationship. Expected result: Deletion is blocked.
- [pending] **MS11-14**: Reload specification. Expected result: FK remains persisted.

##### MS12: Composite foreign keys
Status: [pending]
Objective: Verify FK mappings derived from composite target identity.
- [pending] **MS12-01**: Open FK dialog. Expected result: Source and target entities are available.
- [pending] **MS12-02**: Attempt same source and target. Expected result: Invalid endpoint combination is prevented.
- [pending] **MS12-03**: Open from entity context. Expected result: Source is preselected.
- [pending] **MS12-04**: Verify source and target identity requirements. Expected result: FK requires valid target identity.
- [pending] **MS12-05**: Select target without identity. Expected result: Save is blocked.
- [pending] **MS12-06**: Create single-field mapping. Expected result: Mapping is derived automatically.
- [pending] **MS12-07**: Create composite mapping. Expected result: All target identity components are mapped.
- [pending] **MS12-08**: Source fields missing. Expected result: FK cannot be saved.
- [pending] **MS12-09**: Change target entity. Expected result: Mapping is recalculated.
- [pending] **MS12-10**: Attempt duplicate FK. Expected result: Duplicate is rejected.
- [pending] **MS12-11**: Save valid FK. Expected result: FK is persisted.
- [pending] **MS12-12**: Edit existing FK. Expected result: Endpoints remain locked.
- [pending] **MS12-13**: Cancel edit. Expected result: Original mapping is preserved.
- [pending] **MS12-14**: Request deletion and cancel. Expected result: FK remains.
- [pending] **MS12-15**: Delete FK used by relationship. Expected result: Deletion is blocked.
- [pending] **MS12-16**: Delete FK after removing dependency. Expected result: FK is deleted.
- [pending] **MS12-17**: Simulate deletion failure and retry. Expected result: Error and retry behavior work.

##### MS13: Relationships
Status: [pending]
Objective: Verify that relationships resolve through existing compatible foreign keys.
- [pending] **MS13-01**: Open relationship dialog. Expected result: Entity endpoints are available.
- [pending] **MS13-02**: Attempt same source and target. Expected result: Invalid endpoints are prevented.
- [pending] **MS13-03**: Open from entity context. Expected result: Source is preselected.
- [pending] **MS13-04**: Select valid endpoints. Expected result: Endpoints are accepted.
- [pending] **MS13-05**: Select endpoints without compatible FK. Expected result: User is prompted to define FK first.
- [pending] **MS13-06**: Resolve existing FK mapping. Expected result: Correct field mapping is displayed.
- [pending] **MS13-07**: Multiple FKs between endpoints. Expected result: Ambiguity warning is displayed.
- [pending] **MS13-08**: Verify relationship options after FK resolution. Expected result: Options become available only after resolution.
- [pending] **MS13-09**: Select ONE_TO_ONE. Expected result: Type is saved correctly.
- [pending] **MS13-10**: Select ONE_TO_MANY. Expected result: Type is saved correctly.
- [pending] **MS13-11**: Select MANY_TO_ONE. Expected result: Type is saved correctly.
- [pending] **MS13-12**: Select MANY_TO_MANY. Expected result: Type is saved correctly.
- [pending] **MS13-13**: Set source participation. Expected result: Source participation is saved.
- [pending] **MS13-14**: Set target participation. Expected result: Target participation is saved.
- [pending] **MS13-15**: Test MANDATORY / MANDATORY. Expected result: Both endpoints require participation.
- [pending] **MS13-16**: Test MANDATORY / OPTIONAL. Expected result: Source is mandatory, target optional.
- [pending] **MS13-17**: Test OPTIONAL / MANDATORY. Expected result: Source is optional, target mandatory.
- [pending] **MS13-18**: Test OPTIONAL / OPTIONAL. Expected result: Both endpoints are optional.
- [pending] **MS13-19**: Edit relationship. Expected result: Endpoints remain locked; type and participation can be updated.
- [pending] **MS13-20**: Cancel or confirm deletion. Expected result: Cancellation preserves relationship; confirmation deletes it.

##### MS14: Relationship constraints
Status: [pending]
Objective: Verify relationship-level restrictions and consistency.
- [pending] **MS14-01**: Create relationship with valid FK. Expected result: Relationship is accepted.
- [pending] **MS14-02**: Create relationship with incompatible FK. Expected result: Validation rejects it.
- [pending] **MS14-03**: Verify relationship cardinality against generated data. Expected result: Cardinality violations are detected.
- [pending] **MS14-04**: Verify mandatory source participation. Expected result: Missing required participation is detected.
- [pending] **MS14-05**: Verify mandatory target participation. Expected result: Missing required participation is detected.
- [pending] **MS14-06**: Verify optional participation. Expected result: Missing optional participation is not treated as mandatory failure.
- [pending] **MS14-07**: Edit relationship participation. Expected result: Updated rule is applied.
- [pending] **MS14-08**: Delete relationship. Expected result: Dependent FK can subsequently be removed.

##### MS15: Field constraints
Status: [pending]
Objective: Verify constraint authoring and generated-data validation.
- [pending] **MS15-01**: Open constraint dialog. Expected result: Dialog opens.
- [pending] **MS15-02**: Select target field. Expected result: Correct field is available.
- [pending] **MS15-03**: Select comparison operator. Expected result: Supported operator is accepted.
- [pending] **MS15-04**: Enter comparison value. Expected result: Value is accepted.
- [pending] **MS15-05**: Save valid constraint. Expected result: Constraint is persisted.
- [pending] **MS15-06**: Attempt missing field. Expected result: Save is blocked.
- [pending] **MS15-07**: Attempt unsupported operator. Expected result: Backend rejects it.
- [pending] **MS15-08**: Edit existing constraint. Expected result: Existing values populate.
- [pending] **MS15-09**: Update operator. Expected result: Updated operator is persisted.
- [pending] **MS15-10**: Update comparison value. Expected result: Updated value is persisted.
- [pending] **MS15-11**: Cancel editing. Expected result: Original constraint remains.
- [pending] **MS15-12**: Delete constraint. Expected result: Constraint is removed.
- [pending] **MS15-13**: Validate > constraint. Expected result: Correct values pass; violations fail.
- [pending] **MS15-14**: Validate >= constraint. Expected result: Correct values pass; violations fail.
- [pending] **MS15-15**: Validate < constraint. Expected result: Correct values pass; violations fail.
- [pending] **MS15-16**: Validate <= constraint. Expected result: Correct values pass; violations fail.
- [pending] **MS15-17**: Validate == constraint. Expected result: Correct values pass; violations fail.
- [pending] **MS15-18**: Validate != constraint. Expected result: Correct values pass; violations fail.
- [pending] **MS15-19**: Verify constraint result in validation report. Expected result: Correct status and diagnostic are shown.
- [pending] **MS15-20**: Reload specification. Expected result: Constraint persists.

##### MS16: Entity AI assistance
Status: [pending]
Objective: Verify entity AI proposal lifecycle.
- [pending] **MS16-01**: Load AI examples. Expected result: Examples are displayed.
- [pending] **MS16-02**: Select an example. Expected result: Prompt is populated.
- [pending] **MS16-03**: Submit valid prompt. Expected result: AI request is submitted.
- [pending] **MS16-04**: Submit empty prompt. Expected result: Request is blocked.
- [pending] **MS16-05**: Submit while generating. Expected result: Duplicate request is blocked.
- [pending] **MS16-06**: Receive proposal. Expected result: Proposal is displayed.
- [pending] **MS16-07**: Regenerate proposal. Expected result: New proposal is requested.
- [pending] **MS16-08**: Apply proposal. Expected result: Entity name, description and population populate form.
- [pending] **MS16-09**: Record acceptance. Expected result: Acceptance activity is recorded.
- [pending] **MS16-10**: Edit proposed values. Expected result: User can modify values before saving.
- [pending] **MS16-11**: Cancel without save. Expected result: Specification remains unchanged.
- [pending] **MS16-12**: Simulate AI error. Expected result: Error is displayed and retry is possible.

##### MS17: Field AI assistance
Status: [pending]
Objective: Verify field AI proposal lifecycle.
- [pending] **MS17-01**: Load field AI examples. Expected result: Examples are displayed.
- [pending] **MS17-02**: Select example. Expected result: Prompt is populated.
- [pending] **MS17-03**: Submit valid prompt. Expected result: AI request is submitted.
- [pending] **MS17-04**: Submit empty prompt. Expected result: Request is blocked.
- [pending] **MS17-05**: Submit duplicate request. Expected result: Duplicate request is blocked.
- [pending] **MS17-06**: Receive field name and type proposal. Expected result: Proposal is displayed.
- [pending] **MS17-07**: Receive identity strategy. Expected result: Valid identity configuration is displayed.
- [pending] **MS17-08**: Receive generator and distribution. Expected result: Supported configuration is displayed.
- [pending] **MS17-09**: Receive CLARIFY response. Expected result: Clarification message is displayed.
- [pending] **MS17-10**: Receive UNSUPPORTED response. Expected result: Unsupported request is explained.
- [pending] **MS17-11**: Simulate AI API error. Expected result: Error is displayed.
- [pending] **MS17-12**: Regenerate proposal. Expected result: New proposal is requested.
- [pending] **MS17-13**: Apply proposal. Expected result: Manual field form is populated.
- [pending] **MS17-14**: Review and modify proposal. Expected result: User can change proposed values.
- [pending] **MS17-15**: Save reviewed field. Expected result: Field is persisted.

##### MS18: Identity AI assistance
Status: [pending]
Objective: Verify AI-assisted single and composite identity creation.
- [pending] **MS18-01**: Check AI capability. Expected result: Availability is displayed.
- [pending] **MS18-02**: AI unavailable. Expected result: Prompt and examples are disabled appropriately.
- [pending] **MS18-03**: Submit single-identity example. Expected result: Request is accepted.
- [pending] **MS18-04**: Submit composite-identity example. Expected result: Request is accepted.
- [pending] **MS18-05**: Submit empty prompt. Expected result: Request is blocked.
- [pending] **MS18-06**: Generate proposal. Expected result: Proposal is displayed.
- [pending] **MS18-07**: Receive single-field proposal. Expected result: Correct field is proposed.
- [pending] **MS18-08**: Receive composite proposal. Expected result: Multiple fields are proposed.
- [pending] **MS18-09**: Receive CLARIFY response. Expected result: Clarification is displayed.
- [pending] **MS18-10**: Receive UNSUPPORTED response. Expected result: Unsupported request is explained.
- [pending] **MS18-11**: Simulate AI error. Expected result: Error is displayed.
- [pending] **MS18-12**: Regenerate. Expected result: New proposal is requested.
- [pending] **MS18-13**: Apply proposal. Expected result: Selected fields are updated.
- [pending] **MS18-14**: Record acceptance. Expected result: Acceptance activity is recorded.
- [pending] **MS18-15**: Save identity. Expected result: Reviewed identity is persisted.
- [pending] **MS18-16**: Cancel after applying proposal. Expected result: Persisted identity remains unchanged.

##### MS19: Relationship AI assistance
Status: [pending]
Objective: Verify AI-assisted relationship proposals.
- [pending] **MS19-01**: Check AI capability and examples. Expected result: Availability is displayed.
- [pending] **MS19-02**: Submit relationship prompt. Expected result: Request is accepted.
- [pending] **MS19-03**: Submit empty prompt. Expected result: Request is blocked.
- [pending] **MS19-04**: Receive source and target proposal. Expected result: Endpoints are displayed.
- [pending] **MS19-05**: Receive type and participation proposal. Expected result: Proposed settings are displayed.
- [pending] **MS19-06**: Receive CLARIFY response. Expected result: Clarification is displayed.
- [pending] **MS19-07**: Receive UNSUPPORTED response. Expected result: Unsupported request is explained.
- [pending] **MS19-08**: Simulate API error. Expected result: Error is displayed.
- [pending] **MS19-09**: Regenerate proposal. Expected result: New proposal is requested.
- [pending] **MS19-10**: Apply proposal. Expected result: All five settings populate the form.
- [pending] **MS19-11**: Record acceptance. Expected result: Acceptance activity is recorded.
- [pending] **MS19-12**: Apply proposal without compatible FK. Expected result: Relationship cannot be saved.
- [pending] **MS19-13**: Save reviewed relationship. Expected result: Relationship is persisted.

##### MS20: Constraint AI assistance
Status: [pending]
Objective: Verify AI-assisted constraint proposals.
- [pending] **MS20-01**: Load examples. Expected result: Examples are displayed.
- [pending] **MS20-02**: Submit prompt. Expected result: Request is accepted.
- [pending] **MS20-03**: Submit empty prompt. Expected result: Request is blocked.
- [pending] **MS20-04**: Receive proposal. Expected result: Entity, field, operator and value are displayed.
- [pending] **MS20-05**: Receive CLARIFY response. Expected result: Clarification is displayed.
- [pending] **MS20-06**: Receive UNSUPPORTED response. Expected result: Unsupported request is explained.
- [pending] **MS20-07**: Simulate API error. Expected result: Error is displayed.
- [pending] **MS20-08**: Regenerate. Expected result: New proposal is requested.
- [pending] **MS20-09**: Apply proposal. Expected result: Constraint form is populated.
- [pending] **MS20-10**: Verify field/operator/value. Expected result: Correct values appear.
- [pending] **MS20-11**: Edit proposal value. Expected result: Only the intended value changes.
- [pending] **MS20-12**: Record acceptance. Expected result: Acceptance activity is recorded.
- [pending] **MS20-13**: Save reviewed constraint. Expected result: Constraint is persisted.

##### MS21: CSV wizard
Status: [pending]
Objective: Verify CSV import workflow navigation and state.
- [pending] **MS21-01**: Open CSV wizard. Expected result: Wizard opens.
- [pending] **MS21-02**: Navigate between wizard steps. Expected result: Correct step is displayed.
- [pending] **MS21-03**: Upload valid CSV set. Expected result: Files are accepted.
- [pending] **MS21-04**: Upload unsupported or missing file. Expected result: Validation message appears.
- [pending] **MS21-05**: Navigate backwards. Expected result: Previous state is retained.
- [pending] **MS21-06**: Cancel wizard. Expected result: No unintended import is applied.
- [pending] **MS21-07**: Reopen wizard. Expected result: Initial or persisted state is correct.
- [pending] **MS21-08**: Complete wizard navigation. Expected result: User reaches the intended final step.

##### MS22: CSV validation
Status: [pending]
Objective: Verify CSV schema and data validation.
- [pending] Required CSV files and headers
- [pending] Unexpected columns
- [pending] Missing required values
- [pending] Invalid field types and configuration values
- [pending] Invalid identity definitions
- [pending] Invalid FK source/target fields
- [pending] Invalid relationship endpoints
- [pending] Invalid constraint definitions
- [pending] Row-level errors and actionable diagnostics
- [pending] Validation summary and error location

##### MS23: CSV preview
Status: [pending]
Objective: Verify imported specification preview before applying it.
- [pending] Parsed entities and fields match CSV input
- [pending] Identity fields and ordering are displayed correctly
- [pending] FK and relationship mappings are resolved correctly
- [pending] Constraints appear with the expected field and operator
- [pending] Preview accurately represents validation errors
- [pending] Returning to previous steps does not silently alter input
- [pending] Preview does not persist the specification prematurely

##### MS24: CSV apply and stale protection
Status: [pending]
Objective: Verify applying the imported specification safely.
- [pending] Valid CSV import is applied
- [pending] Imported entities, fields, identities, FKs, relationships and constraints persist
- [pending] Invalid CSV cannot be applied
- [pending] Repeated submission does not create duplicate structures
- [pending] Stale specification state is detected
- [pending] Failed import leaves specification consistent
- [pending] Reload confirms the applied specification
- [pending] User can recover from a failed or stale operation

##### MS25: Model integrity and validation
Status: [pending]
Objective: Verify the integrity of the complete specification and generated dataset.
- [pending] **MS25-01**: Validate field schema. Expected result: Field definitions conform to specification.
- [pending] **MS25-02**: Validate field types. Expected result: Generated values conform to declared types.
- [pending] **MS25-03**: Validate field domains. Expected result: Values conform to configured parameters.
- [pending] **MS25-04**: Validate identity uniqueness. Expected result: No duplicate identity values.
- [pending] **MS25-05**: Validate missing identity components. Expected result: Missing values are detected.
- [pending] **MS25-06**: Validate FK integrity. Expected result: All FK values resolve to parent records.
- [pending] **MS25-07**: Validate composite FK integrity. Expected result: All components map to the correct parent identity.
- [pending] **MS25-08**: Validate dangling references. Expected result: Missing parent references are detected.
- [pending] **MS25-09**: Validate relationship cardinality. Expected result: Cardinality violations are detected.
- [pending] **MS25-10**: Validate mandatory participation. Expected result: Required endpoint participation is enforced.
- [pending] **MS25-11**: Validate optional participation. Expected result: Optional participation is handled correctly.
- [pending] **MS25-12**: Validate field constraints. Expected result: Rule violations are detected.
- [pending] **MS25-13**: Validate semantic uniqueness. Expected result: UNIQUE semantic generation behaves as required.
- [pending] **MS25-14**: Validate semantic vocabulary. Expected result: VOCABULARY values belong to the generated vocabulary.
- [pending] **MS25-15**: Validate population completeness. Expected result: Expected record counts are met.
- [pending] **MS25-16**: Validate conversion errors. Expected result: Invalid conversions are reported.
- [pending] **MS25-17**: Validate no-row or non-evaluated cases. Expected result: NOT_EVALUATED is reported where appropriate.
- [pending] **MS25-18**: Verify final conformance summary. Expected result: Rule-level statuses and diagnostics are consistent.

##### MS26: Persistence and recovery
Status: [pending]
Objective: Verify that Model Studio state survives reload and navigation.
- [pending] Entity creation and update
- [pending] Field creation and configuration
- [pending] Identity and composite identity
- [pending] FK and composite FK
- [pending] Relationship and participation
- [pending] Field and relationship constraints
- [pending] AI-reviewed and manually modified values
- [pending] CSV import
- [pending] Reload after every successful save
- [pending] Navigation away and back
- [pending] Failed save does not corrupt persisted state

##### MS27: Error handling
Status: [pending]
Objective: Verify errors are visible, actionable, and recoverable.
- [pending] API request failures
- [pending] Validation failures
- [pending] Duplicate creation attempts
- [pending] Dependency-blocked deletion
- [pending] AI capability unavailable
- [pending] AI request failure and retry
- [pending] Proposal acceptance tracking failure
- [pending] CSV parsing and validation errors
- [pending] Generation errors
- [pending] Recovery after transient errors
- [pending] Correct loading and busy states
- [pending] No duplicate submission while an operation is in progress

##### MS28: Integrated Model Studio journeys
Status: [pending]
Objective: Verify realistic end-to-end user journeys using Aerospace Enterprise Model v2.
- [pending] **MS28-01**: Create an entity, add fields, save and reload. Expected result: Entity and fields persist.
- [pending] **MS28-02**: Configure identity and generate data. Expected result: Identity values are correct and unique.
- [pending] **MS28-03**: Create parent and child entities with FK. Expected result: Parent-child references are valid.
- [pending] **MS28-04**: Create composite identity and composite FK. Expected result: All components map correctly.
- [pending] **MS28-05**: Create FK-backed relationship. Expected result: Relationship resolves to correct FK.
- [pending] **MS28-06**: Apply relationship participation and generate data. Expected result: Cardinality and participation validate.
- [pending] **MS28-07**: Add constraints and generate data. Expected result: Constraints are evaluated correctly.
- [pending] **MS28-08**: Use AI proposals, review, save and reload. Expected result: Reviewed values are persisted.
- [pending] **MS28-09**: Import Aerospace CSV specification. Expected result: Imported model is equivalent to expected specification.
- [pending] **MS28-10**: Generate complete Aerospace dataset. Expected result: Expected entities and record counts are produced.
- [pending] **MS28-11**: Run generated-data verification. Expected result: Schema, types, keys, FKs, relationships and constraints pass.
- [pending] **MS28-12**: Reload and inspect generated results. Expected result: Results and specification remain consistent.

Additional suite-specific acceptance checks and implementation notes:

- [pending] MS08: Verify that POISSON is rejected for INTEGER and DECIMAL generation because it is not supported by the current validator and generator, despite appearing in the shared distribution vocabulary.
- [pending] MS16: After applying and reviewing an entity AI proposal, save the entity and reload the specification to verify persistence. Acceptance activity and specification persistence are separate operations.
- [pending] MS25: Verify that rule-level statuses remain independently observable as PASSED, FAILED and NOT_EVALUATED.

Cross-cutting evidence required for each applicable test case:
- [pending] Record preconditions, including the data model, entities, fields and dependencies.
- [pending] Record the Playwright UI action and visible result, including dialogs, status, validation messages or notifications.
- [pending] Verify applicable API request payloads, response statuses and validation behavior.
- [pending] Verify persisted specification JSON against the reviewed values.
- [pending] Verify generated output schema, values, keys, references and record counts where applicable.
- [pending] Verify recovery behavior, including cancellation, retry, reload or error handling.

AI-specific execution requirements:
- [pending] Verify proposal generation as a distinct step.
- [pending] Verify applying a proposal to the manual form or selection as a distinct step.
- [pending] Verify the user can review and modify proposed values before saving.
- [pending] Verify saving the reviewed specification as a distinct operation.
- [pending] Reload and independently verify the persisted values.
- [pending] Verify acceptance activity separately; it must not be treated as equivalent to specification persistence.

Execution layers:
- [pending] Authoring flows: Playwright coverage for entities, fields, keys, FKs, relationships, constraints and AI assistance.
- [pending] Import flows: Playwright coverage for CSV wizard, validation, preview and apply.
- [pending] Backend regression: Pytest coverage for specification validation, generation, identity, FK, relationship and constraint logic.
- [pending] Frontend build validation: Angular production build.
- [pending] Integrated E2E: Playwright journeys using Aerospace Enterprise Model v2.
- [pending] Output verification: automated assertions against generated files and actual data correctness.

Aerospace Enterprise Model v2 output verification:
- [pending] Verify entity and field presence.
- [pending] Verify field types and formats.
- [pending] Verify expected record counts.
- [pending] Verify single-field and composite identity uniqueness.
- [pending] Verify FK references and parent-child mapping.
- [pending] Verify relationship cardinality and participation.
- [pending] Verify constraint conformance.
- [pending] Verify semantic value behavior.
- [pending] Verify generated CSV files and headers.
- [pending] Verify there are no missing, unexpected or malformed values.
- [pending] Use fixed seeds wherever the generation interface supports them.
- [pending] For statistical distributions, use sufficiently large populations and tolerances rather than expecting a particular random sequence.

Exit criteria:
- [pending] All 28 suites and their listed test cases are implemented and passing.
- [pending] UI behavior and applicable API/specification persistence outcomes are verified.
- [pending] AI proposal, apply, review, save and reload stages are independently verified.
- [pending] CSV validation, preview, apply and stale-state protection are verified.
- [pending] Aerospace Enterprise Model v2 integrated workflows are executed successfully.
- [pending] Generated datasets and output files are checked for schema, types, formats, record counts, identities, foreign keys, relationships, constraints and semantic behavior.
- [pending] Backend Pytest regression suite passes.
- [pending] Frontend production build passes.
- [pending] Execution evidence and relevant commit references are recorded.

Completion evidence:
- To be populated incrementally as individual test cases and suites are completed.

---
#### WP-07: Full Release Candidate acceptance
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
(forge) e10936535@INM138734 forge %

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
