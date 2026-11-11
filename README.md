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

FORGE uses Playwright for browser-based end-to-end testing. Testing is organized into three workflows: local test development, isolated release acceptance and real-email integration.

### 1. E2E Test Workflows

| Workflow | Purpose | Environment |
|---|---|---|
| Local E2E | Develop, debug and run individual browser tests | Local Angular and FastAPI servers |
| Isolated E2E | Verify the packaged deployment using the complete automated suite | Release candidate deployment |
| Real-email E2E | Verify actual corporate email delivery and magic-link authentication | Release candidate deployment |

### 2. Prerequisites

- Python 3.11 and `uv`
- Node.js and npm
- Playwright and Chromium
- Nginx for isolated deployment testing

Additional release acceptance prerequisites:
- Corporate network/VPN access to the configured Ollama service and required model
- Approved corporate email configuration for real-email testing

Install dependencies when setting up a development environment:

```bash
uv sync --locked --no-dev --no-install-project

cd frontend
npm ci
npx playwright install chromium
cd ..
```

### 3. Local E2E Development

Use the local workflow when developing or debugging individual tests.

Start FORGE:

```bash
./start-forge.sh
```

Open another terminal and run an individual Workspace test:

```bash
cd frontend

npx playwright test \
  --config=playwright.workspace-e2e.config.ts \
  e2e/workspace/workspace-content.spec.ts
```

Run all Workspace tests:

```bash
npx playwright test --config=playwright.workspace-e2e.config.ts
```

The local configuration reuses the saved authentication state when available. If authentication is required, complete the normal magic-link login in the visible browser.

Stop the local services with `Ctrl+C` in the startup terminal.

### 4. Isolated Release Acceptance

Use the release build workflow for final acceptance testing of the deployable application.

From the repository root:

```bash
./scripts/build-deployment.sh
```

The build workflow:

1. Builds the Angular production frontend.
2. Stages the deployment bundle and installs locked backend dependencies.
3. Performs deployment smoke checks.
4. Creates a uniquely identified release candidate and ZIP archive.
5. Verifies deployment archive integrity and sensitive configuration sanitization.
6. Prepares and starts the isolated candidate deployment.
7. Runs the automated Playwright E2E suite.
8. Runs the real-email integration test.
9. Records the release gate result and test evidence.

The isolated candidate uses dedicated local services:

| Service | Address |
|---|---|
| Candidate API | `http://127.0.0.1:18875` |
| Candidate UI | `http://127.0.0.1:18876` |

The workflow automatically checks for stale services belonging to the previous candidate and cleans them up before starting a new candidate. It does not terminate unrelated processes occupying these ports.

Keep the deployment and test terminals open as instructed by the workflow. Complete the visible browser verification when the real-email test requests manual action.

### 5. E2E Test Suites

The frontend defines separate Playwright commands for automated testing and real-email integration:

- `test:e2e:full`: Runs the automated suite, excluding real-email tests.
- `test:e2e:real-email`: Runs the real-email Playwright project.

The release candidate workflow configures the isolated deployment, test environment, sessions and evidence paths before invoking these commands. Use `./scripts/build-deployment.sh` as the normal end-to-end acceptance entry point. Standalone execution requires the same candidate-specific environment configuration.

Coverage includes:

- Authentication and login verification
- Multi-user identities and Workspace access
- Workspace navigation, dashboard and data model interactions
- Data model creation and sample import
- Model validation and population planning
- Real corporate email delivery and magic-link verification

The real-email test requires manual verification in the visible browser. Do not paste magic links or verification tokens into terminal commands or shared logs.

### 6. Test Reports and Evidence

Playwright reports and execution artifacts are retained for review.

Candidate artifacts are retained under:

```text
dist/
├── candidates/
│   └── <candidate-id>/
│       └── FORGE-Deployment-<candidate-id>.zip
└── test-runs/
    └── <candidate-id>/
        ├── evidence/
        │   ├── playwright-report/
        │   └── test-results/
        ├── logs/
        └── release-gate.json
```

Open a candidate's Playwright report:

```bash
cd frontend
npx playwright show-report \
  ../dist/test-runs/<candidate-id>/evidence/playwright-report
```

Review failed tests, screenshots, traces and execution evidence before accepting a candidate.

The release gate records the candidate identity, archive checksum, automated test result, real-email test result and execution evidence location.

A candidate is accepted only when the required automated and real-email tests pass and the release gate reports `PASSED`.

### 7. Test and Release Commands

Run commands from the repository root unless otherwise noted.

| Task | Command |
|---|---|
| Start local FORGE | `./start-forge.sh` |
| Run one Workspace test | `cd frontend && npx playwright test --config=playwright.workspace-e2e.config.ts <spec-file>` |
| Run all local Workspace tests | `cd frontend && npx playwright test --config=playwright.workspace-e2e.config.ts` |
| Run automated isolated suite | `cd frontend && npm run test:e2e:full` |
| Run real-email integration | `cd frontend && npm run test:e2e:real-email` |
| Build and validate release candidate | `./scripts/build-deployment.sh` |
