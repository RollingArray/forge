# FORGE Environment Setup

## Prerequisites

Install the following tools before setting up FORGE:

-   Python 3.11
-   `uv` for Python dependency and environment management
-   Node.js compatible with the Angular application
-   npm

Use the versions required by the repository's dependency and runtime
configuration.

## Python Environment

From the repository root, install the locked Python dependencies:

``` bash
uv sync --locked --no-dev --no-install-project
```

This creates or updates the project's virtual environment using the
dependency versions recorded in `uv.lock`.

## Frontend Environment

Install the frontend dependencies:

``` bash
cd frontend
npm ci
cd ..
```

`npm ci` installs the dependency versions recorded in the frontend
lockfile.

## End-to-End Testing Dependencies

If you plan to run the Playwright end-to-end tests, install the Chromium
browser used by the test suite:

``` bash
cd frontend
npx playwright install chromium
cd ..
```

Additional prerequisites for isolated release acceptance testing are
documented in the [E2E Testing Guide](../testing/e2e-testing-guide.md).

## Next Steps

After installing the dependencies, see:

-   [Local Development](local-development.md) for starting and stopping
    FORGE.
-   [Configuration](configuration.md) for application configuration and
    secret-handling guidance.
