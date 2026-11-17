# FORGE System Architecture

## Architecture Overview

FORGE is organized into a frontend application and a backend generation
platform.

The data model specification is the central contract between the user,
planner, generation engine, and validation services.

## Frontend

The frontend provides the user experience for defining, configuring,
validating, generating, and inspecting synthetic datasets.

### Technology

-   Angular 22
-   Standalone components
-   Strict TypeScript
-   Angular Signals
-   OnPush change detection
-   Tailwind CSS 4
-   Chart.js
-   Cytoscape

## Backend

The backend exposes the application APIs and coordinates specification
management, planning, generation, and validation.

### Technology

-   Python 3.11
-   FastAPI
-   Pydantic v2
-   Uvicorn
-   PyJWT
-   JSON-based persistence
-   pytest for development verification

## Generation Engine

The generation engine is specification driven.

Its responsibilities include:

-   Specification interpretation
-   Generation configuration validation
-   Population planning and feasibility analysis
-   Entity dependency ordering
-   Identity generation
-   Foreign-key resolution
-   Referential integrity
-   Deterministic and semantic value generation
-   Chunked execution and checkpointing
-   Artifact writing and reading
-   Generation quality measurement

The engine uses explicit rules and algorithms wherever possible.

AI-assisted capabilities are applied selectively when semantic
understanding or content generation is useful.

## Specification as the Source of Truth

The data model specification is the central contract between the user,
planner, generation engine, and validation services.

A specification defines what the system contains and how its data
behaves.

Generation planning and execution operate against this specification
rather than relying on assumptions embedded in the application.

## Related Documentation

-   [FORGE Overview](overview.md)
