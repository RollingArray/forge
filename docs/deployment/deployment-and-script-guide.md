# FORGE Deployment and Script Guide

## 1. Purpose

This document describes the FORGE deployment scripts, their responsibilities,
and how they are organized.

The standard release workflow is intentionally kept simple. The normal
entry point for building and validating a deployment candidate is:

```bash
./scripts/build-deployment.sh
````

The other scripts support specialist testing, extracted deployment scenarios,\
or Windows packaging. They are not required for the normal release workflow.

## **2. Standard Release Workflow**

Run the following command from the repository root:

```
./scripts/build-deployment.sh
```

The release workflow coordinates the deployment build and acceptance process,\
including:

1. Angular production frontend build.
2. Backend deployment preparation and dependency setup.
3. Deployment smoke checks and candidate packaging.
4. Deployment archive integrity and configuration checks.
5. Isolated candidate deployment.
6. Automated Playwright E2E execution.
7. Real-email integration testing.
8. Release gate evaluation and evidence generation.
9. Outlook release draft preparation when enabled.

The real-email test requires manual verification in the visible browser.\
Complete that verification through the normal browser workflow. Do not paste\
magic links or verification tokens into terminal commands or shared logs.

The release draft process does not send the email automatically. Review the\
draft, recipient and attachments before taking any further action.

To build and validate without attempting to create an Outlook draft:

```
FORGE_SKIP_OUTLOOK_DRAFT=1 ./scripts/build-deployment.sh
```

## **3. Release-Critical Scripts**

These scripts support the standard release workflow.

| Script                            | Responsibility                                                         |
| --------------------------------- | ---------------------------------------------------------------------- |
| `scripts/build-deployment.sh`     | Main deployment build, candidate orchestration and acceptance workflow |
| `scripts/create-release-draft.py` | Validates a candidate and prepares the Outlook release draft           |
| `scripts/validate-e2e-report.py`  | Validates Playwright E2E report results                                |
| `scripts/e2e/create_sessions.py`  | Creates isolated FORGE E2E user sessions for the candidate             |

Use `build-deployment.sh` as the normal entry point rather than invoking\
individual release stages independently. The workflow configures candidate-\
specific paths, services, sessions and evidence locations.

## **4. E2E Testing Utilities**

The scripts under `scripts/testing/` support separate E2E deployment and\
diagnostic workflows.

| Script                             | Responsibility                                    |
| ---------------------------------- | ------------------------------------------------- |
| `build-e2e-deployment.py`          | Builds a separate isolated E2E deployment package |
| `prepare-full-e2e.sh`              | Prepares a clean full-suite E2E deployment        |
| `run-full-e2e-deployment.sh`       | Extracts and runs the full-suite E2E deployment   |
| `stop-full-e2e-deployment.sh`      | Stops the full-suite E2E services                 |
| `run-extracted-e2e-deployment.sh`  | Runs the separate extracted E2E deployment        |
| `stop-extracted-e2e-deployment.sh` | Stops the extracted E2E services                  |
| `run-archived-e2e-deployment.sh`   | Runs an archived E2E deployment package           |

The full-suite preparation workflow can be started from the repository root:

```
./scripts/testing/prepare-full-e2e.sh
```

The archived E2E runner requires an archive directory:

```
./scripts/testing/run-archived-e2e-deployment.sh \
  dist/forge-e2e/<archive-directory>
```

These utilities are separate from the normal release candidate workflow.\
Use them when specifically investigating or running the corresponding\
isolated deployment scenarios.

### **E2E Authentication Support**

`scripts/e2e/e2e_auth.py` is an E2E-only session bootstrap endpoint.

The E2E deployment builder copies this module into the isolated extracted\
deployment. It must not be registered in the normal FORGE backend.

The normal release workflow uses `scripts/e2e/create_sessions.py` instead.

## **5. Extracted Deployment Utilities**

The scripts under `scripts/deployment-utils/` support rebuilding and running\
an extracted deployment for specialist local verification.

| Script                                    | Responsibility                                                       |
| ----------------------------------------- | -------------------------------------------------------------------- |
| `rebuild-and-run-extracted-deployment.sh` | Rebuilds the deployment, extracts it and starts the local deployment |
| `run-extracted-deployment.sh`             | Runs an already-built extracted deployment                           |

These are optional utilities and are not part of the standard release entry\
point.

Run the rebuild-and-run utility from the repository root:

```
./scripts/deployment-utils/rebuild-and-run-extracted-deployment.sh
```

## **6. Windows Packaging**

The Windows deployment builder is located at:

`scripts/windows/build_windows_deployment.py`

Run it from the repository root:

```
python scripts/windows/build_windows_deployment.py
```

It creates the Windows deployment and data migration ZIP packages under:

`dist/windows-deployment/`

Review the generated packages and migration manifest before transferring\
them.

## **7. Script Directory Layout**

```
scripts/
├── build-deployment.sh
├── create-release-draft.py
├── validate-e2e-report.py
├── e2e/
│   ├── create_sessions.py
│   └── e2e_auth.py
├── testing/
│   ├── build-e2e-deployment.py
│   ├── prepare-full-e2e.sh
│   ├── run-archived-e2e-deployment.sh
│   ├── run-extracted-e2e-deployment.sh
│   ├── run-full-e2e-deployment.sh
│   ├── stop-extracted-e2e-deployment.sh
│   └── stop-full-e2e-deployment.sh
├── deployment-utils/
│   ├── rebuild-and-run-extracted-deployment.sh
│   └── run-extracted-deployment.sh
└── windows/
    └── build_windows_deployment.py
```

## **8. Operating Guidelines**

- Use `./scripts/build-deployment.sh` for the normal release candidate\
  build and acceptance workflow.
- Treat the testing and deployment utility scripts as specialist tools.
- Do not run multiple workflows against the same candidate runtime or ports\
  concurrently.
- Preserve candidate ZIPs, reports, logs and release gate evidence for review.
- Complete real-email verification through the visible browser.
- Review Outlook release drafts and their attachments before sending.
- Do not register the E2E-only authentication endpoint in the normal backend.
- Run commands from the repository root unless a command explicitly states\
  otherwise.