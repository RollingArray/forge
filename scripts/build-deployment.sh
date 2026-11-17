#!/usr/bin/env bash
#
# FORGE Deployment Builder
#
# Author:
# -------
# Ranjoy Sen
#
# Purpose:
# --------
# Builds, packages, and validates the FORGE deployment and release candidate.
#
# Responsibilities:
# -----------------
# - Build the production frontend and deployment package.
# - Validate deployment configuration and corporate AI connectivity.
# - Run deployment smoke checks and collect test evidence.
# - Prepare candidate artifacts and release validation metadata.
# - Support preparation-only execution.

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"
OUTPUT="$ROOT/dist"
STAGE="$OUTPUT/forge-deployment"
ZIP="$OUTPUT/forge-deployment.zip"
TEST_LOG="$OUTPUT/forge-deployment-smoke-test.log"

fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

# Use the repository's authoritative Python environment for release tooling.
PYTHON="$ROOT/.venv/bin/python"

[[ -x "$PYTHON" ]] || fail "Project Python environment is missing."

python_version="$("$PYTHON" -c \
  'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

[[ "$python_version" == "3.11" ]] || \
  fail "Expected Python 3.11, found $python_version."

CANDIDATES="$OUTPUT/candidates"
TEST_RUNS="$OUTPUT/test-runs"
ACTIVE_RUN="$TEST_RUNS/active.json"
PREPARE_ONLY=0

source "$ROOT/scripts/release/deployment_services.sh"
source "$ROOT/scripts/release/deployment_e2e.sh"
source "$ROOT/scripts/release/deployment_candidate.sh"
source "$ROOT/scripts/release/deployment_bundle.sh"




case "${1:-}" in
  "")
    ;;
  "--prepare-only")
    [[ "$#" -eq 1 ]] || fail "Usage: $0 [--prepare-only|--e2e]"
    PREPARE_ONLY=1
    ;;
  "--e2e")
    [[ "$#" -eq 1 ]] || fail "Usage: $0 [--prepare-only|--e2e]"
    run_e2e
    exit 0
    ;;
  *)
    fail "Unknown argument: $1. Usage: $0 [--prepare-only|--e2e]"
    ;;
esac

build_deployment
