# FORGE Testing Strategy

## Purpose

FORGE uses layered verification to check backend behavior, frontend
build integrity, and end-to-end application workflows.

The testing approach is intended to verify both the correctness of
individual backend capabilities and the behavior of the integrated
application.

## Backend Regression Testing

Backend regression testing is performed with pytest.

Backend tests should cover relevant behavior across API, services,
persistence, specification handling, generation, and validation.

When backend behavior changes:

1.  Add or update the relevant backend tests.
2.  Run the focused test module or test group.
3.  Run the broader backend regression suite.
4.  Review failures and warnings before considering the change verified.

Angular unit and component tests are not part of the FORGE
regression-testing approach.

## Frontend Verification

Frontend changes are verified using:

-   Angular production builds
-   The planned Playwright end-to-end tests

The production build checks that the frontend compiles and can be
packaged for deployment.

Playwright end-to-end tests verify application behavior through user
workflows rather than relying on Angular unit or component tests.

## End-to-End Verification

End-to-end testing validates the integrated application across its main
user workflows.

The project distinguishes between:

-   Local E2E development, used while developing and troubleshooting
    test workflows.
-   Isolated release acceptance, used to verify a deployment candidate
    in an isolated environment.
-   Real-email integration, which verifies the email-based
    authentication flow through the visible browser and mailbox
    experience.

See the [E2E Testing Guide](e2e-testing-guide.md) for prerequisites,
commands, workflows, and evidence locations.

## Release Acceptance

A release candidate should be accepted only after its required build,
automated E2E, and real-email checks have completed successfully and the
release gate records a passing result.

The deployment and script responsibilities are documented in the
[Deployment and Script
Guide](../deployment/deployment-and-script-guide.md).

## Related Documentation

-   [Development Guidelines](../standards/development-guidelines.md)
-   [E2E Testing Guide](e2e-testing-guide.md)
-   [Local Model Studio E2E Runbook](local-model-studio-e2e-runbook.md)
-   [Deployment and Script
    Guide](../deployment/deployment-and-script-guide.md)
