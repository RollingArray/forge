# FORGE

### Framework for Generation of Synthetic Engineered Data from Observed Rules

FORGE is a specification-driven framework for engineering synthetic data
from an understanding of the systems, rules, relationships, and
constraints that govern real data.

It generates realistic, coherent, and reproducible synthetic datasets
without depending on large volumes of production data.

> Don't learn the data. Understand the system. Engineer the data.

## What FORGE Does

FORGE uses an explicit system specification to describe:

-   Entities and their fields
-   Identifiers and identity strategies
-   Relationships and foreign-key mappings
-   Referential integrity, business rules, and constraints
-   Statistical characteristics and population requirements
-   Generation strategies and scenarios

The specification is the source of truth for planning, generation, and
validation. FORGE is designed to be domain agnostic, configurable,
transparent, and reproducible.

AI and machine learning are optional capabilities. They can assist with
specification authoring and semantic data generation, but do not replace
the specification, planning, execution, or validation process.

## Architecture at a Glance

FORGE consists of a frontend application and a backend generation
platform.

-   **Frontend:** Angular application for defining, configuring,
    validating, generating, and inspecting synthetic datasets.
-   **Backend:** Python and FastAPI services for specification
    management, planning, generation, and validation.
-   **Generation engine:** Interprets specifications, plans populations,
    resolves identities and relationships, generates records, and
    measures output quality.

The data model specification is the central contract between the user,
planner, generation engine, and validation services.

For details, see the [FORGE Overview](docs/architecture/overview.md) and
[System Architecture](docs/architecture/system-architecture.md).

## Quick Start

### Prerequisites

-   Python 3.11
-   `uv`
-   Node.js compatible with the frontend
-   npm

### Install dependencies

From the repository root:

``` bash
uv sync --locked --no-dev --no-install-project
```

Install frontend dependencies:

``` bash
cd frontend
npm ci
cd ..
```

### Start FORGE

From the repository root:

``` bash
./start-forge.sh
```

The startup script starts the backend and frontend development services.

  Service             URL
  ------------------- ----------------------------
  Frontend            http://localhost:4200
  Backend API         http://127.0.0.1:8000
  API documentation   http://127.0.0.1:8000/docs

Press `Ctrl+C` in the startup terminal to stop the services.

For full setup and operating instructions, see the [Environment
Setup](docs/development/environment-setup.md) and [Local
Development](docs/development/local-development.md) guides.

## Documentation

The documentation is organized by subject.

  ----------------------------------------------------------------------------------------------------------
  Area                    Document                                                   Description
  ----------------------- ---------------------------------------------------------- -----------------------
  Architecture            [FORGE Overview](docs/architecture/overview.md)            Purpose, design
                                                                                     philosophy, and vision

  Architecture            [System                                                    Frontend, backend,
                          Architecture](docs/architecture/system-architecture.md)    generation engine, and
                                                                                     specification

  Development             [Environment Setup](docs/development/environment-setup.md) Prerequisites and
                                                                                     dependency installation

  Development             [Local Development](docs/development/local-development.md) Starting, stopping, and
                                                                                     running services

  Development             [Configuration](docs/development/configuration.md)         Application
                                                                                     configuration and
                                                                                     sensitive settings

  Standards               [Development                                               Frontend, backend, and
                          Guidelines](docs/standards/development-guidelines.md)      generation engineering
                                                                                     practices

  Standards               [Python File                                               Python file-comment
                          Comments](docs/standards/file-comments/python.md)          conventions

  Git                     [Commit Conventions](docs/git/commit-conventions.md)       Commit message
                                                                                     conventions

  Testing                 [Testing Strategy](docs/testing/testing-strategy.md)       Backend, frontend, and
                                                                                     integrated verification
                                                                                     approach

  Testing                 [E2E Testing Guide](docs/testing/e2e-testing-guide.md)     Playwright workflows,
                                                                                     commands, and evidence

  Testing                 [Model Studio E2E                                          Local Model Studio E2E
                          Runbook](docs/testing/local-model-studio-e2e-runbook.md)   procedures

  Deployment              [Release                                                   Release acceptance
                          Acceptance](docs/deployment/release-acceptance.md)         criteria and evidence

  Deployment              [Deployment and Script                                     Deployment scripts and
                          Guide](docs/deployment/deployment-and-script-guide.md)     their responsibilities
  ----------------------------------------------------------------------------------------------------------

## Repository Layout

``` text
forge/
├── backend/       # Backend application and API
├── frontend/      # Angular application and E2E tests
├── docs/          # Project documentation
├── scripts/       # Build, deployment, and testing utilities
├── experiments/   # Experiments and supporting work
├── pyproject.toml # Python project configuration
├── uv.lock        # Locked Python dependencies
└── start-forge.sh # Local development startup
```

## Development and Testing Principles

-   The data model specification is the source of truth for generation.
-   Backend regression testing uses pytest.
-   Frontend verification uses production builds and Playwright
    end-to-end tests.
-   Angular unit and component tests are not part of the project's
    regression-testing approach.
-   Release acceptance requires the required automated checks,
    real-email verification, and a passing release gate.

See the [Development
Guidelines](docs/standards/development-guidelines.md) and [Testing
Strategy](docs/testing/testing-strategy.md) for details.

## Deployment and Release

The standard deployment and release-acceptance workflow is:

``` bash
./scripts/build-deployment.sh
```

Review the [Deployment and Script
Guide](docs/deployment/deployment-and-script-guide.md) and [Release
Acceptance](docs/deployment/release-acceptance.md) before running or
evaluating a release candidate.
