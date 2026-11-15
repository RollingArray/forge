# FORGE Local Model Studio E2E Runbook

## 1. Purpose

This runbook describes how to execute the FORGE Model Studio end-to-end
(E2E) tests against a local development environment.

The local E2E setup is intended to support incremental implementation
and verification of the approved Model Studio test catalogue. It
provides repeatable authentication, test data creation, execution,
cleanup, and troubleshooting guidance.

## 2. Testing architecture

The testing approach separates responsibilities:

  -----------------------------------------------------------------------
  Layer                   Tool                    Purpose
  ----------------------- ----------------------- -----------------------
  Frontend user journeys  Playwright E2E          Verify complete browser
                                                  workflows and visible
                                                  UI behaviour

  Backend regression      Pytest                  Verify API,
                                                  specification,
                                                  validation, and
                                                  generation logic

  Frontend build          Angular production      Detect compilation and
  validation              build                   packaging issues

  Integrated model        Playwright E2E          Exercise the Aerospace
  journey                                         Enterprise Model v2
                                                  workflow

  Generated output        Automated assertions    Verify schema, values,
  verification                                    keys, relationships,
                                                  constraints, and output
                                                  files
  -----------------------------------------------------------------------

**Testing standards**

-   Use Playwright for frontend end-to-end coverage.
-   Use Pytest for backend regression coverage.
-   Use the Angular production build for frontend build validation.
-   Do not add Angular unit or component tests.
-   Preserve the approved suite IDs, case IDs, scenarios, and expected
    outcomes.
-   Implement and execute the catalogue incrementally, in small groups.
-   Use Aerospace Enterprise Model v2 as the primary integrated test
    model.
-   Use deterministic AI responses or mocks for tests that must not
    depend on a live AI service.
-   Keep test data isolated and clean up only resources created by the
    test.

## 3. One-time environment setup

The local development environment uses:

-   Angular frontend: `http://localhost:4200`
-   FastAPI backend: `http://127.0.0.1:8000`
-   Playwright configuration: `frontend/playwright.config.ts`

From the repository root:

``` bash
cd /Users/e10936535/forge
```

Start the backend if it is not already running:

``` bash
.venv/bin/python -m uvicorn app.main:app \
  --app-dir backend/api \
  --reload \
  --host 127.0.0.1 \
  --port 8000 \
  --env-file .env
```

Start the Angular development server in a separate terminal:

``` bash
cd /Users/e10936535/forge/frontend
npm start
```

Keep both services running while executing local browser tests.

## 4. Local test authentication

Local E2E tests use dedicated FORGE test identities rather than a
personal or corporate user session.

  ---------------------------------------------------------------------------------
  Role                    Email                             Display name
  ----------------------- --------------------------------- -----------------------
  Owner                   `forge.owner@collins.com`         FORGE E2E Owner

  Contributor             `forge.contributor@collins.com`   FORGE E2E Contributor

  Viewer                  `forge.viewer@collins.com`        FORGE E2E Viewer
  ---------------------------------------------------------------------------------

Create or refresh the local sessions from the repository root:

``` bash
cd /Users/e10936535/forge

set -a
source .env
set +a

.venv/bin/python scripts/e2e/create_sessions.py \
  backend/api \
  frontend/playwright/.auth/local-sessions.json

unset FORGE_JWT_SECRET
```

The local authentication setup reads the Owner session and creates the
Playwright storage state used by the local Chromium project.

**Security requirements**

-   Do not print, paste, or commit session JSON files.
-   Do not expose the JWT signing secret in terminal output or
    documentation.
-   Keep generated authentication files under the configured Playwright
    authentication directory.
-   Ensure local session and storage-state files remain excluded from
    Git.

## 5. Running Model Studio E2E tests

Navigate to the frontend directory:

``` bash
cd /Users/e10936535/forge/frontend
```

Run the local authentication fixture verification:

``` bash
npx playwright test \
  --config=playwright.config.ts \
  --grep "MS-FIX-01"
```

Run the Model Studio entry and navigation suite:

``` bash
npx playwright test \
  --config=playwright.config.ts \
  --grep "MS01" \
  --workers=1 \
  --reporter=list
```

Run all local E2E tests:

``` bash
npx playwright test \
  --config=playwright.config.ts \
  --workers=1 \
  --reporter=list
```

Open the HTML report:

``` bash
npx playwright show-report
```

### Visual execution and configurable browser speed

Playwright supports configurable visual slowdown for local test
demonstrations and debugging.

The setting is centralised in:

`frontend/playwright.config.ts`

Use the environment variable:

`FORGE_E2E_SLOW_MO_MS`

The value is specified in milliseconds and controls the delay between
browser actions.

Visual slowdown applies only when running tests in headed mode. Normal
headless execution is unaffected.

#### Run headed tests with a configurable delay

Example: 500 milliseconds between browser actions.

``` bash
FORGE_E2E_SLOW_MO_MS=500 npx playwright test \
  --config=playwright.config.ts \
  --headed \
  --workers=1 \
  --reporter=list
```

Other useful values:

  Setting                       Behaviour
  ----------------------------- ----------------------
  `FORGE_E2E_SLOW_MO_MS=300`    300 ms delay
  `FORGE_E2E_SLOW_MO_MS=500`    500 ms delay
  `FORGE_E2E_SLOW_MO_MS=1000`   1 second delay
  Variable omitted              Normal browser speed

#### Run headed tests at normal speed

``` bash
npx playwright test \
  --config=playwright.config.ts \
  --headed \
  --workers=1
```

#### Run normal headless regression tests

``` bash
npx playwright test \
  --config=playwright.config.ts \
  --workers=1
```

No visual slowdown is applied to headless execution.

**Important:** This setting is global to the configured Chromium test
project. Individual test files do not need to implement their own
browser slowdown logic.

### Guided demonstration test

The guided demonstration is a separate walkthrough intended for a
visible demonstration of the workspace, specification import, Model
Studio, and validation journey.

To run it with a pause at each demonstration checkpoint:

``` bash
FORGE_DEMO_PAUSE_SECONDS=2 npx playwright test \
  --config=playwright.config.ts \
  e2e/data-model/model-studio-demo.spec.ts \
  --workers=1 \
  --headed \
  --reporter=list
```

Set `FORGE_DEMO_PAUSE_SECONDS` to the desired number of seconds. If
omitted or set to `0`, the demonstration runs without intentional
checkpoint pauses. This setting is specific to the guided demonstration
test. The global `FORGE_E2E_SLOW_MO_MS` setting controls browser action
speed for headed runs.

## 6. Adding a new E2E test case

Before adding a test:

1.  Confirm the approved suite and test-case ID in `BACKLOG.md`.
2.  Preserve the existing case ID, scenario, and expected outcome.
3.  Reuse the shared workspace and Model Studio fixtures where
    appropriate.
4.  Use a unique test-owned model for scenarios that create or modify a
    model.
5.  Ensure cleanup removes only resources created by that test.
6.  Keep tests independent so they can run repeatedly.
7.  Use deterministic AI mocking for AI-assisted scenarios where
    external AI availability is not part of the test objective.

Place Model Studio tests under:

`frontend/e2e/data-model/`

Run the smallest relevant test group first, then run the broader
regression group.

## 7. Test data and cleanup strategy

-   Use uniquely named test-owned models for normal Model Studio
    scenarios.
-   Use dedicated models for destructive scenarios.
-   Use the official Aerospace Enterprise Model v2 sample for integrated
    coverage.
-   Do not modify or delete user-owned or shared models.
-   Confirm that a test has exactly one matching test-owned model before
    performing destructive cleanup.
-   Clean up test-created models even when a test fails, where the
    fixture supports teardown.
-   Keep test authentication identities separate from personal accounts.

The Aerospace integrated journey should verify more than successful job
completion. Output verification should cover:

-   Entity and field presence.
-   Field types and formats.
-   Expected record counts.
-   Single-field and composite identity uniqueness.
-   Foreign-key references and parent-child mapping.
-   Relationship cardinality and participation.
-   Constraint conformance.
-   Semantic value behaviour.
-   Generated CSV files and headers.
-   Missing, unexpected, or malformed values.

Use fixed seeds wherever the generation interface supports them. For
statistical distribution checks, use sufficiently large populations and
sensible tolerances rather than expecting a specific random sequence.

## 8. Debugging and troubleshooting

### Frontend or backend is not reachable

Confirm that the Angular and FastAPI services are running at the
configured local addresses.

### Authentication setup fails

-   Confirm that the backend is running.
-   Confirm that the local `.env` file provides a valid
    `FORGE_JWT_SECRET`.
-   Re-run the session creation command from the repository root.
-   Do not paste session contents or signing secrets into logs or chat.

### A Playwright test fails

Run only the failing test or suite first:

``` bash
npx playwright test \
  --config=playwright.config.ts \
  --grep "authenticate as local FORGE E2E Owner" \
  --workers=1 \
  --reporter=list
```

Inspect the terminal output and the Playwright HTML report. For
browser-visible debugging, use `--headed`. Add a temporary visual delay
through `FORGE_E2E_SLOW_MO_MS` rather than adding hard-coded waits to
individual regression tests.

### Test data remains after a failed run

Inspect the workspace and identify the exact test-owned model before
removing anything. Do not use broad cleanup commands or delete models
based only on a partial name match.

## 9. Testing standards

-   Keep backend regression tests in Pytest.
-   Do not add Angular unit or component tests.
-   Use the production Angular build as the frontend build validation
    gate.
-   Use Playwright E2E for browser behaviour and user journeys.
-   Keep test cases deterministic, isolated, and repeatable.
-   Avoid arbitrary sleeps in regression tests. Prefer Playwright
    assertions and explicit state-based waits.
-   Use visual slowdown only for headed demonstration or debugging runs.
-   Record test evidence in `BACKLOG.md` as each approved case is
    completed.
-   Work in small, reviewable groups.
-   Do not commit changes until the changes and evidence have been
    reviewed and explicitly approved.

## 10. Future isolated deployment testing

Local development E2E is the first validation stage. A separate isolated
candidate deployment can be used later to validate a production-like
packaged build without relying on the local development servers.

The isolated deployment workflow should:

-   Build and verify a candidate deployment package.
-   Use a separate runtime and dedicated E2E sessions.
-   Keep secrets outside the deployment package.
-   Run the isolated Playwright configuration against the candidate UI
    and API.
-   Capture test reports and failure evidence separately from local
    runs.
-   Avoid modifying the local development environment or user data.

Use the dedicated isolated deployment scripts and
`playwright.e2e-isolated.config.ts` for that workflow. Do not substitute
the isolated deployment configuration for the local
`playwright.config.ts` workflow.

------------------------------------------------------------------------

## Runbook outcome

This runbook provides the local execution path for FORGE Model Studio
E2E development and demonstration. The approved test catalogue remains
the source of truth for suite IDs, case IDs, scenarios, and expected
outcomes.
