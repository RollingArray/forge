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

## Troubleshooting

### Python module not found

Ensure the root environment is synchronized:

```
cd /Users/e10936535/forge
uv sync --locked --no-dev --no-install-project
```

The backend should use:

```
/Users/e10936535/forge/.venv/bin/python
```

Avoid mixing the root `.venv`, backend `.venv`, and system Python environments.

### Port already in use

The startup script checks ports 8000 and 4200 before starting.

Inspect the processes using these ports:

```
lsof -nP -iTCP:8000 -iTCP:4200 -sTCP:LISTEN
```

Stop only the relevant stale development process before restarting FORGE.

### Frontend dependencies missing

From the frontend directory:

```
cd /Users/e10936535/forge/frontend
npm ci
```

### Backend or frontend startup errors

Inspect the corresponding log:

```
tail -100 /tmp/forge-dev-logs/backend.log
tail -100 /tmp/forge-dev-logs/frontend.log
```