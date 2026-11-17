# FORGE End-to-End Testing Guide

## Overview

FORGE uses Playwright to verify integrated application workflows.

The project supports three related E2E workflows:

1.  **Local E2E development** for developing and troubleshooting tests
    against a locally running FORGE environment.
2.  **Isolated release acceptance** for testing a packaged deployment
    candidate in an isolated environment.
3.  **Real-email integration** for verifying email-based authentication
    through the visible browser and mailbox experience.

## Prerequisites

The E2E workflows require:

-   Python 3.11
-   `uv`
-   Node.js and npm
-   Playwright and its Chromium browser
-   A configured corporate network or VPN connection when required by
    the configured Ollama service and model
-   Nginx for isolated release acceptance
-   Approved corporate email configuration for the real-email
    integration test

Install the project dependencies from the repository root:

``` bash
uv sync --locked --no-dev --no-install-project
```

Install frontend dependencies and the Playwright Chromium browser:

``` bash
cd frontend
npm ci
npx playwright install chromium
```

## Local E2E Development

Start the local application from the repository root:

``` bash
./start-forge.sh
```

Run the focused Workspace content test:

``` bash
cd frontend
npx playwright test --config=playwright.workspace-e2e.config.ts e2e/workspace/workspace-content.spec.ts
```

Run the Workspace E2E suite:

``` bash
npx playwright test --config=playwright.workspace-e2e.config.ts
```

The local workflow can use saved authentication state or the normal
magic-link flow, depending on the test setup.

Stop the local application with `Ctrl+C` in the terminal running
`start-forge.sh`.

## Isolated Release Acceptance

The standard release acceptance workflow is:

``` bash
./scripts/build-deployment.sh
```

The workflow builds the Angular production application, stages the
packaged application and locked backend dependencies, performs smoke
checks, creates a deployment candidate, verifies candidate integrity and
sensitive-configuration sanitization, and runs the isolated acceptance
checks.

The isolated candidate uses:

  Service            Port
  --------------- -------
  Candidate API     18875
  Candidate UI      18876

The workflow manages stale services belonging to a previous candidate.
It is designed not to terminate unrelated services.

Complete the visible browser verification required by the real-email
integration flow. Do not paste magic links or authentication tokens into
a terminal or shared logs.

## E2E Test Suites

The frontend package scripts include:

  -----------------------------------------------------------------------
  Command                             Purpose
  ----------------------------------- -----------------------------------
  `npm run test:e2e:full`             Runs the automated full E2E suite,
                                      excluding the real-email
                                      integration test

  `npm run test:e2e:real-email`       Runs the real-email Playwright
                                      project
  -----------------------------------------------------------------------

Run these commands from the `frontend` directory.

The broader E2E coverage includes:

-   Authentication
-   Multi-user workflows
-   Workspace behavior
-   Navigation and dashboard behavior
-   Data model creation and sample import
-   Model validation
-   Population planning
-   Real-email magic-link authentication

Use the isolated release acceptance workflow for the normal release
verification path. Standalone test commands may require the
corresponding candidate environment to have already been prepared and
running.

## Test Reports and Evidence

Release acceptance evidence is written beneath:

``` text
dist/test-runs/<candidate-id>/
```

The evidence structure includes:

``` text
evidence/
  playwright-report/
  test-results/
logs/
release-gate.json
```

The deployment candidate archive is written beneath:

``` text
dist/candidates/<candidate-id>/FORGE-Deployment-<candidate-id>.zip
```

View a Playwright report from the `frontend` directory:

``` bash
npx playwright show-report ../dist/test-runs/<candidate-id>/evidence/playwright-report
```

The release gate records candidate identity, checksum, automated test
result, real-email result, and evidence location.

A release candidate is accepted only when the required automated and
real-email checks pass and the release gate reports `PASSED`.

## Authentication and Email Safety

The real-email integration test verifies the email-based authentication
flow.

Complete the required mailbox and browser interaction visibly. Do not
copy magic links or authentication tokens into terminal commands, source
files, or shared logs.

Use only the approved corporate email configuration for this workflow.

## Related Documentation

-   [Testing Strategy](testing-strategy.md)
-   [Local Model Studio E2E Runbook](local-model-studio-e2e-runbook.md)
-   [Deployment and Script
    Guide](../deployment/deployment-and-script-guide.md)
-   [Environment Setup](../development/environment-setup.md)
