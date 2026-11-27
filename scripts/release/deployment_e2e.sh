#!/usr/bin/env bash
#
# FORGE Deployment Test Orchestration
#
# Author:
# -------
# Ranjoy Sen
#
# Purpose:
# --------
# Runs backend regression and end-to-end release validation.
#
# Responsibilities:
# -----------------
# - Run the complete backend Pytest regression suite.
# - Validate automated and real-email Playwright reports.
# - Record E2E release evidence and failures.
# - Coordinate optional Outlook draft preparation.

run_backend_pytest() {
  local log="$OUTPUT/backend-pytest.log"
  local junit="$OUTPUT/backend-pytest.xml"
  local summary="$OUTPUT/backend-pytest-summary.json"

  [[ -x "$PYTHON" ]] || fail "Project Python environment is missing."
  [[ -f "$ROOT/.env" ]] || fail "Repository .env is required for backend Pytest."

  printf '\n== Backend: Complete Pytest regression suite ==\n'

  if ! (
    set -a
    source "$ROOT/.env"
    set +a

    if [[ -z "${FORGE_JWT_SECRET:-}" || ${#FORGE_JWT_SECRET} -lt 32 ]]; then
      printf 'ERROR: FORGE_JWT_SECRET is missing or invalid.\n' >&2
      exit 1
    fi

    cd "$ROOT/backend/api"
    "$PYTHON" -m pytest -q --junitxml="$junit"
  ) 2>&1 | tee "$log"; then
    fail "Backend Pytest failed. Review $log. Candidate creation stopped."
  fi

  "$PYTHON" "$ROOT/scripts/release/evidence.py" pytest-summary \
    --report "$junit" \
    --log "$log" \
    --output "$summary"

  printf 'PASS: Backend Pytest release gate.\n'

}

record_e2e_failure() {
  local failed_stage="$1"

  "$PYTHON" "$ROOT/scripts/release/evidence.py" e2e-failure \
    --active "$ACTIVE_RUN" \
    --run-dir "$run_dir" \
    --candidate-id "$candidate_id" \
    --sha "$candidate_sha" \
    --started-at "$started_at" \
    --failed-stage "$failed_stage"
}

run_e2e() {
  command -v npm >/dev/null 2>&1 || fail "npm is required."
  [[ -x "$PYTHON" ]] || fail "Project Python environment is missing."
  command -v curl >/dev/null 2>&1 || fail "curl is required."

  [[ -f "$ACTIVE_RUN" ]] || fail "No active candidate test run. Run ./scripts/build-deployment.sh first."

  local candidate_id candidate_sha run_dir api_pid nginx_pid runtime
  IFS=$'\t' read -r candidate_id candidate_sha run_dir api_pid nginx_pid runtime < <(
    "$PYTHON" - "$ACTIVE_RUN" <<'PY_ACTIVE'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text())
for key in ("candidate_id", "sha256", "run_dir", "api_pid", "nginx_pid", "runtime"):
    if key not in d:
        raise SystemExit(f"Active run metadata missing: {key}")
print("\t".join(str(d[key]) for key in (
    "candidate_id", "sha256", "run_dir", "api_pid", "nginx_pid", "runtime"
)))
PY_ACTIVE
  )

  local candidate_dir="$CANDIDATES/$candidate_id"
  local candidate_zip="$candidate_dir/FORGE-Deployment-${candidate_id}.zip"

  [[ -d "$runtime" ]] || fail "Candidate runtime is missing."
  [[ -f "$run_dir/sessions.json" ]] || fail "Candidate E2E sessions are missing."
  [[ -f "$run_dir/secrets/jwt.secret" ]] || fail "Candidate runtime secret is missing."

  "$PYTHON" - "$ROOT" "$candidate_dir" "$candidate_id" "$candidate_sha" <<'PY_CANDIDATE_VALIDATION'
import sys
from pathlib import Path

repo_root, candidate_dir, candidate_id, expected_sha = sys.argv[1:]

repo_root = str(Path(repo_root).resolve())
sys.path.insert(0, repo_root)

from scripts.release.validation import (
    ValidationError,
    validate_candidate_artifacts,
    validate_pytest_summary,
)

try:
    result = validate_candidate_artifacts(
        candidate_dir,
        candidate_id,
        expected_sha=expected_sha,
    )
    validate_pytest_summary(result["manifest"].get("backend_pytest"))
except (ValidationError, TypeError, ValueError) as exc:
    raise SystemExit(f"Candidate validation failed: {exc}")

print(f"Candidate archive validation: PASS ({result['sha256']})")
print("Candidate backend Pytest evidence: PASS")
PY_CANDIDATE_VALIDATION
  [[ -f "$candidate_zip" ]] || fail "Candidate deployment archive is missing."

  local status
  status="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status",""))' "$ACTIVE_RUN")"
  [[ "$status" == "PREPARED" ]] || fail "Candidate test status is '$status', not PREPARED. Build a fresh candidate for another test run."

  kill -0 "$api_pid" 2>/dev/null || fail "Candidate API process is not running. Restart by building a fresh candidate."
  kill -0 "$nginx_pid" 2>/dev/null || fail "Candidate Nginx process is not running. Restart by building a fresh candidate."

  curl --silent --show-error --fail http://127.0.0.1:18875/health >/dev/null \
    || fail "Candidate API health check failed."
  curl --silent --show-error --fail http://127.0.0.1:18876/ | grep -q '<html' \
    || fail "Candidate frontend health check failed."

  mkdir -p "$run_dir/logs" "$run_dir/evidence" "$run_dir/reports"
  check_corporate_ollama "$runtime/backend/api/config/ai.json" "$run_dir/logs"

  export FORGE_E2E_BASE_URL="http://127.0.0.1:18876"
  export FORGE_E2E_SESSIONS_FILE="$run_dir/sessions.json"
  export FORGE_E2E_EVIDENCE_DIR="$run_dir/evidence"
  export FORGE_E2E_CANDIDATE_ID="$candidate_id"
  export FORGE_E2E_DATA_MODEL_ROOT="$runtime/backend/api/data/data_model"

  printf '\nCandidate: %s\n' "$candidate_id"
  printf 'SHA-256: %s\n' "$candidate_sha"
  printf 'Runtime: %s\n' "$runtime"
  printf 'UI: %s\n' "$FORGE_E2E_BASE_URL"
  printf '\nPlaywright test inventory will be calculated from its JSON reports.\n'

  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  printf '\n== 1/2: Run automated E2E suite ==\n'
  export FORGE_E2E_JSON_REPORT="$run_dir/reports/automated.json"
  if ! (
    cd "$FRONTEND"
    npm run test:e2e:full
  ) 2>&1 | tee "$run_dir/logs/playwright-full.log"; then
    record_e2e_failure "automated-e2e"
    fail "Automated E2E suite failed. Candidate is not eligible for promotion."
  fi

  if ! "$PYTHON" "$ROOT/scripts/release/e2e_reports.py" \
    --report "$run_dir/reports/automated.json" \
    --output "$run_dir/reports/automated-summary.json"; then
    record_e2e_failure "automated-e2e-report-validation"
    fail "Automated E2E report did not satisfy release criteria."
  fi

  printf '\n== 2/2: Run visible real-email E2E test ==\n'
  printf 'Complete the email verification in the visible browser when prompted.\n'

  export FORGE_E2E_JSON_REPORT="$run_dir/reports/real-email.json"
  if ! (
    cd "$FRONTEND"
    npm run test:e2e:real-email
  ) 2>&1 | tee "$run_dir/logs/playwright-real-email.log"; then
    record_e2e_failure "real-email-e2e"
    fail "Real-email E2E test failed. Candidate is not eligible for promotion."
  fi

  if ! "$PYTHON" "$ROOT/scripts/release/e2e_reports.py" \
    --report "$run_dir/reports/real-email.json" \
    --output "$run_dir/reports/real-email-summary.json"; then
    record_e2e_failure "real-email-e2e-report-validation"
    fail "Real-email E2E report did not satisfy release criteria."
  fi

  "$PYTHON" "$ROOT/scripts/release/evidence.py" e2e-pass \
    --active "$ACTIVE_RUN" \
    --run-dir "$run_dir" \
    --candidate-id "$candidate_id" \
    --sha "$candidate_sha" \
    --started-at "$started_at"

  if [[ "${FORGE_SKIP_OUTLOOK_DRAFT:-0}" == "1" ]]; then
    printf '\nOutlook draft creation skipped by FORGE_SKIP_OUTLOOK_DRAFT=1.\n'
  else
    printf '\nPreparing Outlook release draft...\n'
    if "$PYTHON" "$ROOT/scripts/release/release_draft.py" --candidate-id "$candidate_id"; then
      printf 'Outlook draft preparation completed. Review it before sending.\n'
    else
      printf 'WARNING: Release gate passed, but Outlook draft preparation needs attention.\n' >&2
    fi
  fi

  printf '\nPASS: Both E2E stages completed.\n'
  printf 'Candidate %s is eligible for promotion.\n' "$candidate_id"
  printf 'Release evidence: %s\n' "$run_dir"
}
