# FORGE Release Acceptance

## Purpose

Release acceptance verifies that a packaged FORGE deployment candidate
is complete, internally consistent, and passes the required application
checks.

The standard release acceptance workflow is driven by:

``` bash
./scripts/build-deployment.sh
```

See the [Deployment and Script Guide](deployment-and-script-guide.md)
for script responsibilities and supporting utilities.

## Acceptance Stages

The release workflow covers the following stages:

1.  **Production build**: Build the Angular frontend for production.
2.  **Backend packaging**: Stage the backend application and locked
    dependencies.
3.  **Smoke checks**: Verify that the packaged application can start and
    respond as expected.
4.  **Candidate creation**: Produce the deployment candidate archive.
5.  **Integrity and configuration checks**: Verify candidate integrity
    and check that sensitive configuration is sanitized.
6.  **Isolated deployment**: Run the candidate in an isolated
    environment.
7.  **Automated E2E tests**: Execute the required Playwright acceptance
    suite.
8.  **Real-email integration**: Verify email-based authentication
    through the visible browser and mailbox workflow.
9.  **Release gate**: Record the results and determine whether the
    candidate meets the acceptance criteria.

## Required Acceptance Criteria

A candidate is accepted only when all required checks have completed
successfully.

  -----------------------------------------------------------------------
  Area                                Acceptance expectation
  ----------------------------------- -----------------------------------
  Production build                    Frontend production build completes
                                      successfully

  Backend package                     Backend and locked dependencies are
                                      included

  Smoke checks                        Packaged services pass the required
                                      startup and response checks

  Candidate integrity                 Candidate identity and checksum are
                                      verified

  Configuration safety                Sensitive configuration is
                                      sanitized from the deployment
                                      artifact

  Automated E2E                       Required automated Playwright tests
                                      pass

  Real-email integration              Required real-email authentication
                                      verification passes

  Release gate                        `release-gate.json` records
                                      `PASSED`
  -----------------------------------------------------------------------

A successful build by itself is not sufficient for release acceptance.

## Candidate and Evidence Locations

Deployment candidates are written beneath:

``` text
dist/candidates/<candidate-id>/
```

The candidate archive follows this naming pattern:

``` text
FORGE-Deployment-<candidate-id>.zip
```

Test evidence is written beneath:

``` text
dist/test-runs/<candidate-id>/
```

The test-run directory includes:

``` text
evidence/
  playwright-report/
  test-results/
logs/
release-gate.json
```

The release gate records candidate identity, checksum, automated test
result, real-email result, and evidence location.

## Real-Email Verification

The real-email integration verifies the email-based authentication flow.

Complete the required mailbox and browser interaction visibly. Do not
paste magic links or authentication tokens into terminal commands,
source files, or shared logs.

Use only the approved corporate email configuration for this workflow.

## Reviewing Acceptance Results

Before accepting a candidate:

1.  Confirm the candidate ID and archive are the expected ones.
2.  Review the automated Playwright report and test results.
3.  Confirm the real-email integration result.
4.  Review the release gate.
5.  Confirm that the release gate status is `PASSED`.

Do not treat a candidate as accepted when required evidence is missing
or a required check has failed.

## Related Documentation

-   [Testing Strategy](../testing/testing-strategy.md)
-   [E2E Testing Guide](../testing/e2e-testing-guide.md)
-   [Deployment and Script Guide](deployment-and-script-guide.md)
