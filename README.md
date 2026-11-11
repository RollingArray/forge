# FORGE

### Framework for Generation of Synthetic Engineered Data from Observed Rules

**FORGE** is a specification-driven framework for engineering synthetic data from an understanding of the systems, rules, relationships, and constraints that govern real data.

It is designed to generate realistic, coherent, and reproducible synthetic datasets without depending on large volumes of existing production data.

---

## The Name

**FORGE** is inspired by the idea of a forge: a place where raw material is deliberately shaped into something useful through defined processes and controlled conditions.

That is the philosophy behind the framework.

FORGE takes observed rules and system knowledge and uses them to deliberately shape synthetic data.

```text
Observed Rules
      |
      v
System Specification
      |
      v
    FORGE
      |
      v
Synthetic Engineered Data
````

The name represents what the framework does rather than forcing it into an acronym.

> Don't learn the data. Understand the system. Engineer the data.

## The Idea

FORGE generates synthetic data from an understanding of the system rather than depending on large volumes of existing data.

It uses an explicit, structured specification describing:

- Entities and their fields
- Identifiers and identity strategies
- Relationships between entities
- Foreign-key mappings and referential integrity
- Business rules and constraints
- Statistical characteristics
- Population requirements
- Generation strategies and scenarios

The specification becomes the source of truth for generation.

This makes the generation process transparent, configurable, and independent of any single enterprise domain.

## Design Philosophy

FORGE is:

- Domain agnostic
- Specification driven
- Statistics first
- Deterministic where possible
- Transparent by design
- Configurable
- Reproducible
- Validation driven

AI and machine learning are optional capabilities, not architectural dependencies.

Where AI is used, it assists the engineering process, including specification authoring and semantic data generation. It does not replace the underlying specification, planning, execution, or validation logic.

## Vision

FORGE aims to provide a general-purpose engineering foundation for synthetic data generation across enterprise systems such as:

- SAP
- PLM
- MES
- ERP
- CRM
- Custom applications
- Relational databases
- Other structured information systems

Domain knowledge should enter through the system specification, not through domain-specific logic embedded in the core framework.

This allows the same generation foundation to be applied across different enterprise domains while keeping domain-specific knowledge explicit and configurable.

## Core Principle

> Generate from the rules, not from the data.

Instead of requiring large volumes of real data to learn how a system behaves, FORGE starts with what is known about the system.

```
Entities
   +
Relationships
   +
Constraints
   +
Statistics
   +
Generation Rules
        |
        v
      FORGE
        |
        v
 Synthetic Dataset
        |
        v
Independent Validation
```

The result is synthetic data engineered according to an explicit understanding of the system.

## Architecture

FORGE is organized into a frontend application and a backend generation platform.

### Frontend

The frontend provides the user experience for defining, configuring, validating, generating, and inspecting synthetic datasets.

Technology:

- Angular 22
- Standalone components
- Strict TypeScript
- Angular Signals
- OnPush change detection
- Tailwind CSS 4
- Chart.js
- Cytoscape

### Backend

The backend exposes the application APIs and coordinates specification management, planning, generation, and validation.

Technology:

- Python 3.11
- FastAPI
- Pydantic v2
- Uvicorn
- PyJWT
- JSON-based persistence
- pytest for development verification

### Generation Engine

The generation engine is specification driven. Its responsibilities include:

- Specification interpretation
- Generation configuration validation
- Population planning and feasibility analysis
- Entity dependency ordering
- Identity generation
- Foreign-key resolution
- Referential integrity
- Deterministic and semantic value generation
- Chunked execution and checkpointing
- Artifact writing and reading
- Generation quality measurement

The engine uses explicit rules and algorithms wherever possible. AI-assisted capabilities are applied selectively when semantic understanding or content generation is useful.

### Specification as the Source of Truth

The data model specification is the central contract between the user, planner, generation engine, and validation services.

A specification defines what the system contains and how its data behaves. Generation planning and execution operate against this specification rather than relying on assumptions embedded in the application.

## Repository Structure

The repository is organized into the following primary areas:

```
forge/
|
+-- backend/
|   +-- api/
|       +-- app/
|       |   +-- api/
|       |   +-- core/
|       |   +-- models/
|       |   +-- repositories/
|       |   +-- services/
|       |   +-- main.py
|       |
|       +-- config/
|       +-- data/
|       +-- .venv/
|
+-- frontend/
|   +-- src/
|   |   +-- app/
|   |   +-- environments/
|   +-- package.json
|
+-- experiments/
|
+-- .venv/
+-- pyproject.toml
+-- uv.lock
+-- start-forge.sh
+-- README.md
```

The root Python environment and dependency lockfile are used for backend development. The backend data directory contains persisted data models and generated artifacts.

## Prerequisites

Install the following development tools:

| Tool    | Requirement                                     |
| ------- | ----------------------------------------------- |
| Python  | 3.11                                            |
| uv      | Python dependency and environment management    |
| Node.js | Compatible with the installed Angular toolchain |
| npm     | Node package management                         |

The repository uses:

- `pyproject.toml` for Python project dependencies.
- `uv.lock` for reproducible Python dependency resolution.
- `frontend/package.json` for frontend dependencies.

## Initial Setup

Clone or open the FORGE repository:

```
cd /Users/e10936535/forge
```

### 1. Set up Python dependencies

From the repository root:

```
uv sync --locked --no-dev --no-install-project
```

This creates or synchronizes the root `.venv` using the versions recorded in `uv.lock`.

### 2. Set up frontend dependencies

```
cd frontend
npm ci
```

Return to the repository root:

```
cd ..
```

These setup steps are normally required only when preparing a new development environment or when dependencies change.

## Starting FORGE

FORGE provides a unified development startup script that launches both the backend API and frontend development server.

From the repository root:

```
./start-forge.sh
```

The script:

1. Checks the required development tools.
2. Verifies the Python environment and frontend dependencies.
3. Checks whether the required ports are available.
4. Synchronizes Python dependencies against `uv.lock`.
5. Starts the FastAPI backend.
6. Starts the Angular frontend.
7. Keeps backend and frontend logs separate.
8. Monitors both development servers.
9. Stops both servers when the script receives Ctrl+C.

No manual Python environment activation is required.

### Development URLs

| Service                   | URL                                                                             |
| ------------------------- | ------------------------------------------------------------------------------- |
| FORGE frontend            | [http://localhost:4200](http://localhost:4200?utm_source=chatgpt.com)           |
| Backend API               | [http://127.0.0.1:8000](http://127.0.0.1:8000?utm_source=chatgpt.com)           |
| Swagger API documentation | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs?utm_source=chatgpt.com) |

### Stopping FORGE

Press:

```
Ctrl+C
```

The startup script handles shutdown of both development servers.

### Logs

The startup script stores logs separately under:

```
/tmp/forge-dev-logs/
```

Files:

```
backend.log
frontend.log
```

These logs can be inspected when troubleshooting startup or runtime issues.

## Running Services Individually

The unified startup script is the recommended development workflow.

For troubleshooting, the services can also be started separately.

### Backend

From the repository root:

```
./.venv/bin/python -m uvicorn app.main:app \
  --app-dir backend/api \
  --reload \
  --host 127.0.0.1 \
  --port 8000
```

### Frontend

```
cd frontend
npm start
```

## Configuration

Application configuration is maintained separately from the core generation engine.

Backend configuration includes settings for:

- AI provider integration
- Email delivery
- Application services

AI provider configuration is maintained under:

```
backend/api/config/ai.json
```

Email configuration is maintained under:

```
backend/api/config/email.json
```

Local configuration should be managed carefully. Do not commit credentials, API keys, passwords, or other secrets to source control.

## Development Guidelines

The project follows a few important engineering principles.

### Frontend

- Use standalone Angular components.
- Maintain strict TypeScript typing.
- Prefer Angular Signals for reactive component state.
- Use OnPush change detection.
- Keep API communication in typed Angular services.
- Use the central API configuration.
- Avoid direct HTTP calls from components.

### Backend

- Use Python 3.11.
- Use FastAPI and Pydantic for API and data contracts.
- Keep business logic in services rather than API route handlers.
- Use repository abstractions for persistence.
- Keep generation logic specification driven.
- Preserve referential integrity during generation.
- Keep validation independent from generation execution.

### Generation

- The specification is the source of truth.
- Validate generation configuration before execution.
- Preserve entity identity and foreign-key semantics.
- Plan entity dependencies before generating data.
- Keep population feasibility separate from generation execution.
- Measure generated-data quality independently.

## End-to-End (E2E) Testing

FORGE uses two primary E2E environments:

1. **Local development:** Tests run against the live Angular and FastAPI development servers.
2. **Isolated acceptance:** Tests run against the compiled frontend and packaged backend extracted from `dist/forge-e2e`.

Use local development for writing, debugging and refining individual tests. Use the isolated deployment for final acceptance against the deployable application package.

Real corporate email integration is a separate test because it requires actual email delivery and manual inbox verification.

### E2E Test Coverage

| Test area | Coverage | Execution mode |
|---|---|---|
| Login | Login UI, validation, error and success scenarios | Mocked API |
| Login verification | Verification states and responses | Mocked API |
| Multi-user | Owner, Contributor and Viewer identities, independent sessions and Workspace access | Isolated backend |
| Workspace | Workspace entry, dashboard, data models and model dialogs | Development or isolated |
| WP02 | End-to-end model creation, sample import, validation and population planning | Isolated deployment |
| Real email | Actual magic-link delivery and session verification | Separate integration test |

The multi-user test verifies independent identities and Workspace access. It does not, by itself, prove that every role-specific authorization rule is enforced.

WP02 creates a uniquely named Data Model and intentionally retains it for inspection and acceptance evidence. Workspace fixture tests create and clean up their own temporary test models.

### 1. Prerequisites

Run commands from the repository root unless otherwise stated.

```bash
cd /Users/e10936535/forge
````

Required for local development:

- Python 3.11
- `uv`
- Node.js and npm
- Playwright browser dependencies

Nginx is additionally required for the packaged isolated E2E deployment.

Synchronize backend dependencies when required:

```
uv sync --locked --no-dev --no-install-project
```

Install frontend dependencies when required:

```
cd frontend
npm ci
npx playwright install chromium
cd ..
```

Do not commit credentials, bootstrap keys, tokens or other secrets.

### 2. Local E2E Development

Use the local development environment while creating, debugging and refining Playwright tests. Do not start an isolated deployment for individual test runs.

#### Step 1: Start FORGE

From the repository root:

```
./start-forge.sh
```

Keep this terminal open.

| Service          | URL                     |
| ---------------- | ----------------------- |
| Angular frontend | `http://localhost:4200` |
| FastAPI backend  | `http://127.0.0.1:8000` |

#### Step 2: Run an individual test file

Open a second terminal:

```
cd /Users/e10936535/forge/frontend
npx playwright test --config=playwright.workspace-e2e.config.ts e2e/workspace/workspace-content.spec.ts
```

Replace the spec filename with the file being developed.

#### Step 3: Run all Workspace tests

```
npx playwright test --config=playwright.workspace-e2e.config.ts
```

This runs all `e2e/workspace/**/*.spec.ts` files against the local Angular server, using one worker.

#### Authentication

The local configuration uses `playwright/.auth/user.json`.

- If the saved authentication state exists, Playwright reuses it.
- If it does not exist, Playwright runs `e2e/auth.setup.ts`.
- Complete the normal FORGE magic-link login in the visible browser.
- Playwright saves the authenticated session for subsequent test runs.

If the saved session expires, remove `playwright/.auth/user.json` from the frontend directory and rerun the tests to trigger authentication setup again.

#### Development workflow

Develop and verify individual spec files locally. Once test development is complete, proceed to the isolated acceptance and real-email workflows.

Stop the local development servers with `Ctrl+C` in the startup terminal.

### 3. Build the Isolated E2E Deployment

The isolated deployment package contains:

- The compiled Angular frontend.
- The FastAPI backend.
- The locked Python dependency configuration.
- An E2E-only authentication endpoint injected into the extracted deployment.
- An independent E2E bootstrap key and JWT configuration.

The E2E authentication endpoint is added to the deployment package only. It is not added to the source backend.

#### Step 1: Stop deployments using the current package

Before rebuilding the package, stop any deployment that uses it.

For a full-suite deployment, press `Ctrl+C` in its deployment terminal or use:

```
./scripts/stop-full-e2e-deployment.sh
```

For a standard extracted deployment, use:

```
./scripts/stop-extracted-e2e-deployment.sh
```

Do not move or archive a package while services extracted from it are running.

An archived deployment has its own runtime directory. Do not stop or modify it as part of the normal full-suite workflow.

#### Step 2: Build the Angular frontend

```
npm --prefix frontend run build
```

Confirm that the compiled frontend exists:

```
test -f frontend/dist/forge-ui/browser/index.html \
  && echo "PASS: Compiled frontend exists." \
  || echo "FAIL: Frontend build output is missing."
```

#### Step 3: Preserve the previous deployment package

The build script refuses to overwrite an existing `dist/forge-e2e` directory.

Archive the existing package before building a fresh one:

```
if [ -d dist/forge-e2e ]; then
  ARCHIVE="dist/forge-e2e-archive-$(date +%Y%m%d-%H%M%S)"
  mv dist/forge-e2e "$ARCHIVE"
  echo "Previous package preserved at: $ARCHIVE"
fi
```

Only do this after stopping deployments that use the package.

This preserves the previous package, runtime data, logs and reports. Do not delete old archives as part of the normal build process.

#### Step 4: Build the deployment package

```
python3 scripts/build-e2e-deployment.py
```

The build creates:

```
dist/forge-e2e/
├── forge-deployment/
├── forge-e2e-deployment.zip
└── e2e-bootstrap.key
```

The bootstrap key is kept outside the ZIP package. Treat it as sensitive.

The build script validates its inputs and refuses to overwrite an existing output directory. If the build fails, inspect the error and preserve the existing files.

### 4. Run the Full Isolated E2E Suite

The full-suite deployment uses dedicated ports.

| Service           | URL / location                        |
| ----------------- | ------------------------------------- |
| FastAPI           | `http://127.0.0.1:18875`              |
| Angular UI        | `http://127.0.0.1:18876`              |
| Runtime directory | `dist/forge-e2e/forge-e2e-full-suite` |
| Bootstrap key     | `dist/forge-e2e/e2e-bootstrap.key`    |

Important: Follow the steps below in order. Never archive a runtime while its deployment processes are running.

#### Step 1: Stop any previous full-suite deployment

If a previous full-suite deployment is running, stop it first.

Preferred method: switch to the terminal where `./scripts/run-full-e2e-deployment.sh` was started and press `Ctrl+C`. Wait for the shutdown messages.

Alternatively, from another terminal, while the runtime is still at its original location:

```
cd /Users/e10936535/forge
./scripts/stop-full-e2e-deployment.sh
```

Do not archive or move the runtime before stopping its services. The backend and Nginx configuration use paths inside that runtime.

#### Step 2: Verify both dedicated ports are free

```
for port in 18875 18876; do
  if lsof -nP -iTCP:$port -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
    echo "FAIL: Port $port is still in use."
    exit 1
  fi
done

echo "PASS: Full-suite E2E ports are free."
```

If either port is occupied, identify the process before proceeding. Do not blindly kill processes or start another deployment.

#### Step 3: Preserve any previous runtime

Only after the previous deployment has stopped and both ports are free, archive the existing runtime if it exists.

Run from the repository root:

```
cd /Users/e10936535/forge

RUNTIME="dist/forge-e2e/forge-e2e-full-suite"
ARCHIVE="dist/forge-e2e/forge-e2e-full-suite-archive-$(date +%Y%m%d-%H%M%S)"

if [ -d "$RUNTIME" ]; then
  mv "$RUNTIME" "$ARCHIVE"
  echo "Previous runtime preserved at: $ARCHIVE"
else
  echo "No previous full-suite runtime to archive."
fi
```

This preserves the previous runtime's logs, extracted deployment and diagnostic evidence.

Do not delete previous runtime archives as part of the normal test workflow.

#### Step 4: Start the isolated deployment

Open a dedicated terminal:

```
cd /Users/e10936535/forge
./scripts/run-full-e2e-deployment.sh
```

Keep this terminal open during testing.

The launcher:

1. Extracts the deployment ZIP into the full-suite runtime directory.
2. Installs the locked backend dependencies.
3. Starts FastAPI.
4. Configures and starts Nginx.
5. Checks API health and frontend availability.
6. Keeps the deployment running until interrupted.

If startup fails, read the error and inspect the processes and runtime before retrying. Do not repeatedly run the launcher while either port is occupied.

#### Step 5: Run the full Playwright suite

Open a second terminal:

```
cd /Users/e10936535/forge/frontend
npm run test:e2e:full
```

This command configures Playwright to use:

- UI base URL: `http://127.0.0.1:18876`
- E2E deployment root: `../dist/forge-e2e`
- Bootstrap key: `../dist/forge-e2e/e2e-bootstrap.key`
- Configuration: `playwright.e2e-isolated.config.ts`

The suite includes isolated authentication setup, login, verification, multi-user, Workspace and WP02 tests. Tests tagged `REAL EMAIL E2E` are excluded.

#### Step 6: Review results

Playwright output and artifacts are stored under:

```
frontend/
├── playwright-report/
│   └── isolated-e2e/
└── test-results/
    └── isolated-e2e/
```

Open the HTML report:

```
cd /Users/e10936535/forge/frontend
npx playwright show-report playwright-report/isolated-e2e
```

Review failed tests, screenshots, traces and video evidence before accepting the run.

WP02 intentionally retains its generated Data Model. Inspect it through the FORGE UI after the run.

#### Step 7: Stop the full-suite deployment

Press `Ctrl+C` in the deployment terminal and wait for its shutdown messages.

Alternatively, from another terminal:

```
cd /Users/e10936535/forge
./scripts/stop-full-e2e-deployment.sh
```

Verify that both ports are free before archiving the runtime or starting another deployment.

The stop operation preserves the runtime directory, logs and test data. Do not move the runtime until the services have stopped.


### 5. Real Corporate Email Integration

Use this workflow to verify actual corporate email delivery, manual magic-link verification, JWT persistence and authenticated Workspace access.

**Important:** The real-email test uses the full-suite isolated deployment on port `18876`. It does not use the standard extracted deployment on port `18866`.

#### Step 1: Check whether the full-suite deployment is already running

From a separate terminal:

```bash
curl -I http://127.0.0.1:18876/
curl http://127.0.0.1:18876/health
```

Expected backend response:

```json
{"status":"ok"}
```

If both checks succeed, reuse the running deployment. **Do not run the deployment launcher again and do not archive its runtime.** Continue to Step 2.

If the deployment is unavailable, follow Section 4, *Run the Full Isolated E2E Suite*, to start it.

That procedure includes:
- Confirming the previous deployment has stopped.
- Checking that ports `18875` and `18876` are free.
- Preserving the previous runtime before starting a new deployment.
- Starting the full-suite deployment and verifying its health.

Keep the deployment terminal open.

#### Step 2: Verify the real-email test endpoint

The real-email test must target:

```text
http://127.0.0.1:18876
```

The full-suite deployment must have valid runtime email configuration. Corporate SMTP credentials must be supplied through the approved local configuration process. They are not included in the deployment package.

#### Step 3: Run the real-email test

Open another terminal:

```bash
cd /Users/e10936535/forge/frontend
npm run test:e2e:real-email
```

The command uses:

- Playwright configuration: `playwright.e2e-isolated.config.ts`
- Project: `real-email`
- UI base URL: `http://127.0.0.1:18876`
- Deployment root: `../dist/forge-e2e`
- Bootstrap key: `../dist/forge-e2e/e2e-bootstrap.key`

#### Step 4: Complete manual email verification

The test opens a visible Chromium browser and requests a real magic link.

When the terminal displays `ACTION REQUIRED`:

1. Open the actual email delivered to the configured corporate mailbox.
2. Copy the complete magic link.
3. Switch to the visible FORGE Chromium browser.
4. Paste the link into the browser address bar.
5. Press Enter.
6. Allow Playwright to complete the verification and Workspace checks.

Important:

- Do not paste the magic link into the terminal.
- Do not inject the token into browser storage.
- Do not navigate programmatically to the verification URL.
- Complete the manual verification while the test is waiting.

#### Step 5: Review the result

A successful run confirms:

- Magic-link request accepted by the isolated backend.
- Actual email link verified successfully.
- JWT session persisted in browser storage.
- Authenticated email matches the requested identity.
- Workspace welcome header displays the expected profile name.
- Workspace metrics, data models, templates and activity APIs are accessible.

Review the Playwright report and test evidence before accepting the result.

#### Important operating rules

- Reuse a healthy full-suite deployment.
- Never archive a runtime while its services are running.
- If a new deployment is required, follow Section 4 in order.
- Do not start the standard extracted deployment on port `18866` for this test.
- Never expose bootstrap keys, SMTP credentials, magic links or verification tokens in logs or shared documentation.

### 6. Legacy Deployment Maintenance (Standard and Archived)

These launchers are retained for historical deployment maintenance and archived test reruns. They are not part of the normal test-development or final acceptance workflow.

| Workflow               | Launcher                                  | Default ports       |
| ---------------------- | ----------------------------------------- | ------------------- |
| Full isolated suite    | `scripts/run-full-e2e-deployment.sh`      | API 18875, UI 18876 |
| Standard extracted E2E | `scripts/run-extracted-e2e-deployment.sh` | API 18865, UI 18866 |
| Archived E2E rerun     | `scripts/run-archived-e2e-deployment.sh`  | API 18865, UI 18866 |

Use the full-suite launcher for normal complete isolated acceptance.

Use the archived launcher only when deliberately rerunning a preserved historical deployment. It requires the archive directory as an argument:

```
scripts/run-archived-e2e-deployment.sh \
  dist/forge-e2e-archive-YYYYMMDD-HHMMSS
```

Do not run two deployments on the same ports simultaneously.

### 7. E2E Runtime Data and Preservation

E2E runtime data is intentionally kept separate from source-controlled application data.

The deployment runtime can contain:

- Test users and authentication records.
- Data Models created during testing.
- Data Model access records.
- Activity and execution artifacts.
- API and Nginx logs.
- Playwright reports and failure evidence.

The full-suite stop operation preserves the runtime directory. The deployment launcher refuses to reuse an existing runtime directory.

Always stop the deployment and verify that its ports are free before archiving or moving its runtime. Never move a runtime while its backend or Nginx processes are running.

Before rebuilding or rerunning, inspect existing runtime data and archives. Do not delete runtime data simply to make a startup command succeed.

### 8. Quick Command Reference

Run from the repository root unless otherwise noted.

| Task                            | Command                                                                                                                  |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Start local FORGE               | `./start-forge.sh`                                                                                                       |
| Run one Workspace spec          | `cd frontend && npx playwright test --config=playwright.workspace-e2e.config.ts e2e/workspace/workspace-content.spec.ts` |
| Run all Workspace tests locally | `cd frontend && npx playwright test --config=playwright.workspace-e2e.config.ts`                                         |
| Build frontend                  | `npm --prefix frontend run build`                                                                                        |
| Build isolated package          | `python3 scripts/build-e2e-deployment.py`                                                                                |
| Start full isolated deployment  | `./scripts/run-full-e2e-deployment.sh`                                                                                   |
| Stop full isolated deployment   | `./scripts/stop-full-e2e-deployment.sh`                                                                                  |
| Run full isolated suite         | `cd frontend && npm run test:e2e:full`                                                                                   |
| Run real-email test             | `cd frontend && npm run test:e2e:real-email`                                                                             |
| View isolated HTML report       | `cd frontend && npx playwright show-report playwright-report/isolated-e2e`                                               |
