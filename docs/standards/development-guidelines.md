# FORGE Development Guidelines

These guidelines describe the engineering principles for the frontend,
backend, and generation engine.

## Frontend

-   Use Angular standalone components.
-   Maintain strict TypeScript typing.
-   Use Angular Signals for reactive state where appropriate.
-   Use OnPush change detection.
-   Keep API communication in typed services rather than making direct
    HTTP calls from components.
-   Use the central API configuration rather than hard-coding service
    endpoints.
-   Keep components focused on presentation and user interaction.

## Backend

-   Use Python 3.11.
-   Use FastAPI for API endpoints and Pydantic for data validation and
    typed models.
-   Keep route handlers focused on HTTP concerns. Place application
    logic in service modules.
-   Use repository abstractions for persistence access.
-   Keep behavior specification driven rather than embedding domain
    assumptions in application code.
-   Preserve data integrity and validate inputs at appropriate
    boundaries.
-   Keep validation independent from generation wherever possible.

## Generation

-   Treat the data model specification as the source of truth.
-   Validate generation configuration before execution.
-   Preserve identity and foreign-key integrity.
-   Plan entity dependencies before generating records.
-   Keep population feasibility analysis separate from generation
    execution.
-   Make generation behavior deterministic where possible.
-   Keep quality measurement and verification independent from the
    generation process.

## General Engineering Practices

-   Prefer clear, maintainable implementations over unnecessary
    complexity.
-   Keep responsibilities separated between UI, API, services,
    persistence, generation, and validation.
-   Make assumptions explicit and keep domain-specific rules in the
    specification.
-   Add or update backend regression tests when backend behavior
    changes.
-   Use frontend production builds and the planned Playwright end-to-end
    tests for frontend validation. Angular unit and component tests are
    not part of the project's regression-testing approach.

## Related Documentation

-   [System Architecture](../architecture/system-architecture.md)
-   [Testing Strategy](../testing/testing-strategy.md)
-   [Commit Conventions](../git/commit-conventions.md)
