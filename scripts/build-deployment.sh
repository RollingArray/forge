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

CANDIDATES="$OUTPUT/candidates"
TEST_RUNS="$OUTPUT/test-runs"
ACTIVE_RUN="$TEST_RUNS/active.json"
PREPARE_ONLY=0


check_corporate_ollama() {
  local ai_config="$1" logs_dir="$2" config_values base_url model tags_file
  mkdir -p "$logs_dir"

  config_values="$(python3 - "$ai_config" <<'PY_OLLAMA_CONFIG'
import json, sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text())
if config.get("provider") != "ollama":
    raise SystemExit("Candidate AI provider is not Ollama.")

base_url = str(config.get("base_url", "")).strip().rstrip("/")
model = str(config.get("model", "")).strip()

if not base_url.startswith(("http://", "https://")) or not model:
    raise SystemExit("Candidate Ollama URL or model is missing.")

print(f"{base_url}\t{model}")
PY_OLLAMA_CONFIG
)" || fail "Could not read candidate Ollama configuration."

  base_url="${config_values%%$'\t'*}"
  model="${config_values#*$'\t'}"

  [[ -n "$base_url" && -n "$model" ]] || fail "Invalid candidate Ollama configuration."

  tags_file="$logs_dir/ollama-tags.json"

  printf '\nChecking corporate Ollama: %s\n' "$base_url"

  if ! curl --silent --show-error --fail \
    --connect-timeout 5 --max-time 20 \
    "${base_url}/api/tags" -o "$tags_file"; then
    fail "Corporate Ollama is unreachable at $base_url. Connect to the corporate VPN/network and retry. Local fallback is disabled."
  fi

  python3 - "$tags_file" "$model" <<'PY_OLLAMA_MODEL' ||
import json, sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text())
models = payload.get("models", [])
names = {
    str(item.get("name", ""))
    for item in models
    if isinstance(item, dict)
}

if sys.argv[2] not in names:
    print("Available models:", ", ".join(sorted(names)) or "<none>", file=sys.stderr)
    raise SystemExit(1)

print(f"PASS: Corporate Ollama model available: {sys.argv[2]}")
PY_OLLAMA_MODEL
    fail "Required model '$model' is not available on corporate Ollama at $base_url."
}

cleanup_previous_candidate_services() {
  local active_data run_dir runtime candidate_id api_pid nginx_pid
  local api_command nginx_command listener_pids pid worker_parent worker_command
  local port remaining

  printf '\nChecking for previous FORGE candidate services...\n'

  if [[ ! -f "$ACTIVE_RUN" ]]; then
    for port in 18875 18876; do
      if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        fail "Port $port is occupied but no active-run ownership metadata exists. Nothing was terminated."
      fi
    done
    printf 'No previous FORGE candidate services are running.\n'
    return 0
  fi

  active_data="$(python3 - "$ACTIVE_RUN" "$TEST_RUNS" <<'PY_ACTIVE_CLEANUP'
import json, sys
from pathlib import Path

active_path, test_runs = map(Path, sys.argv[1:])
active = json.loads(active_path.read_text())

candidate_id = str(active.get("candidate_id", ""))
run_dir_value = str(active.get("run_dir", ""))

if not candidate_id or not run_dir_value:
    raise SystemExit("Active run does not identify a candidate and run directory.")

test_runs = test_runs.resolve()
run_dir = Path(run_dir_value).resolve()

if not run_dir.is_relative_to(test_runs) or run_dir == test_runs:
    raise SystemExit("Active run directory is outside the FORGE test-runs directory.")

metadata_path = run_dir / "runtime-processes.json"
if not metadata_path.is_file():
    raise SystemExit("Runtime process ownership metadata is missing.")

metadata = json.loads(metadata_path.read_text())

if metadata.get("candidate_id") != candidate_id:
    raise SystemExit("Runtime process candidate ID does not match active run.")
if Path(str(metadata.get("run_dir", ""))).resolve() != run_dir:
    raise SystemExit("Runtime process run directory does not match active run.")

runtime = (run_dir / "runtime" / "forge-deployment").resolve()
if Path(str(metadata.get("runtime", ""))).resolve() != runtime:
    raise SystemExit("Runtime process path does not match the expected candidate runtime.")

api_pid = metadata.get("api_pid")
nginx_pid = metadata.get("nginx_pid")

if (
    not isinstance(api_pid, int)
    or not isinstance(nginx_pid, int)
    or api_pid <= 1
    or nginx_pid <= 1
    or api_pid == nginx_pid
):
    raise SystemExit("Runtime process PIDs are invalid.")

if metadata.get("api_port") != 18875 or metadata.get("nginx_port") != 18876:
    raise SystemExit("Runtime process ports do not match the FORGE candidate ports.")

print("\t".join((candidate_id, str(run_dir), str(runtime), str(api_pid), str(nginx_pid))))
PY_ACTIVE_CLEANUP
)" || fail "Could not verify previous candidate ownership. No processes were terminated."

  IFS=$'\t' read -r candidate_id run_dir runtime api_pid nginx_pid <<< "$active_data"

  api_command="$(ps -ww -p "$api_pid" -o command= 2>/dev/null || true)"
  nginx_command="$(ps -ww -p "$nginx_pid" -o command= 2>/dev/null || true)"

  if [[ -n "$api_command" ]]; then
    [[ "$api_command" == "$runtime/.venv/bin/python -m uvicorn app.main:app"* ]] \
      && [[ "$api_command" == *"--port 18875"* ]] \
      || fail "API PID $api_pid does not match the recorded candidate runtime. Nothing was terminated."
  fi

  if [[ -n "$nginx_command" ]]; then
    [[ "$nginx_command" == *"nginx: master process"* ]] \
      && [[ "$nginx_command" == *"-p $run_dir/nginx/"* ]] \
      && [[ "$nginx_command" == *"-c $run_dir/nginx/nginx.conf"* ]] \
      || fail "Nginx PID $nginx_pid does not match the recorded candidate runtime. Nothing was terminated."
  fi

  listener_pids="$(lsof -nP -t -iTCP:18875 -sTCP:LISTEN 2>/dev/null | sort -u || true)"
  if [[ -n "$api_command" ]]; then
    [[ "$listener_pids" == "$api_pid" ]] \
      || fail "API port listener does not match recorded candidate PID $api_pid. Nothing was terminated."
  else
    [[ -z "$listener_pids" ]] \
      || fail "API port is occupied but its recorded process is absent. Nothing was terminated."
  fi

  listener_pids="$(lsof -nP -t -iTCP:18876 -sTCP:LISTEN 2>/dev/null | sort -u || true)"
  if [[ -n "$nginx_command" ]]; then
    [[ -n "$listener_pids" ]] \
      || fail "Nginx master exists but no process owns port 18876. Nothing was terminated."

    printf '%s\n' "$listener_pids" | grep -Fxq "$nginx_pid" \
      || fail "Recorded Nginx master PID $nginx_pid is not a port listener. Nothing was terminated."

    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      [[ "$pid" == "$nginx_pid" ]] && continue

      worker_parent="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
      worker_command="$(ps -ww -p "$pid" -o command= 2>/dev/null || true)"

      [[ "$worker_parent" == "$nginx_pid" ]] \
        && [[ "$worker_command" == "nginx: worker process"* ]] \
        || fail "Port 18876 is held by PID $pid, which is not a verified worker of Nginx master $nginx_pid. Nothing was terminated."
    done <<< "$listener_pids"
  else
    [[ -z "$listener_pids" ]] \
      || fail "Nginx port is occupied but its recorded master process is absent. Nothing was terminated."
  fi

  if [[ -z "$api_command" && -z "$nginx_command" ]]; then
    printf 'Recorded candidate processes are already stopped.\n'
    return 0
  fi

  printf 'Verified candidate %s process ownership.\n' "$candidate_id"

  if [[ -n "$nginx_command" ]]; then
    printf 'Stopping recorded Nginx master PID %s...\n' "$nginx_pid"
    kill -TERM "$nginx_pid" 2>/dev/null || true
  fi

  if [[ -n "$api_command" ]]; then
    printf 'Stopping recorded API PID %s...\n' "$api_pid"
    kill -TERM "$api_pid" 2>/dev/null || true
  fi

  for attempt in $(seq 1 20); do
    remaining=0
    for port in 18875 18876; do
      if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        remaining=1
      fi
    done
    [[ "$remaining" -eq 0 ]] && break
    sleep 1
  done

  for port in 18875 18876; do
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      lsof -nP -iTCP:"$port" -sTCP:LISTEN >&2 || true
      fail "Port $port did not close after recorded candidate shutdown."
    fi
  done

  printf 'PASS: Recorded candidate services stopped. Ports 18875 and 18876 are free.\n'
}

run_backend_pytest() {
  local log="$OUTPUT/backend-pytest.log"
  local junit="$OUTPUT/backend-pytest.xml"
  local summary="$OUTPUT/backend-pytest-summary.json"

  [[ -x "$ROOT/.venv/bin/python" ]] || fail "Root .venv Python is missing."
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
    "$ROOT/.venv/bin/python" -m pytest -q --junitxml="$junit"
  ) 2>&1 | tee "$log"; then
    fail "Backend Pytest failed. Review $log. Candidate creation stopped."
  fi

  python3 - "$junit" "$log" "$summary" <<'PY_PYTEST_SUMMARY'
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

report_path, log_path, summary_path = map(Path, sys.argv[1:])
if not report_path.is_file():
    raise SystemExit("Pytest JUnit report is missing.")
if not log_path.is_file():
    raise SystemExit("Pytest console log is missing.")

root = ET.parse(report_path).getroot()

test_cases = []
for case in root.iter():
    if case.tag.rsplit("}", 1)[-1] != "testcase":
        continue

    outcome = next(
        (
            child.tag.rsplit("}", 1)[-1]
            for child in case
            if child.tag.rsplit("}", 1)[-1] in {"failure", "error", "skipped"}
        ),
        None,
    )
    status = (
        "SKIPPED" if outcome == "skipped"
        else "FAILED" if outcome in {"failure", "error"}
        else "PASSED"
    )
    test_cases.append({
        "classname": case.get("classname", ""),
        "name": case.get("name", ""),
        "time_seconds": float(case.get("time", 0)),
        "status": status,
    })

tests = len(test_cases)
failures = 0
errors = 0
skipped = 0
passed = 0

for element in root.iter():
    if element.tag.rsplit("}", 1)[-1] != "testcase":
        continue
    outcome_tags = {
        child.tag.rsplit("}", 1)[-1]
        for child in element
    }
    if "error" in outcome_tags:
        errors += 1
    elif "failure" in outcome_tags:
        failures += 1
    elif "skipped" in outcome_tags:
        skipped += 1
    else:
        passed += 1

duration = sum(case["time_seconds"] for case in test_cases)

log_text = log_path.read_text(errors="replace")
warning_match = re.search(
    r"\b(\d+)\s+warnings?\s+in\s+[\d.]+s\b",
    log_text,
)
warning_count = int(warning_match.group(1)) if warning_match else 0

warning_details = []
start = re.search(r"=+ warnings summary =+\s*", log_text, re.IGNORECASE)
if start:
    remainder = log_text[start.end():]
    end = re.search(r"\n-- Docs:", remainder)
    section = remainder[:end.start()] if end else remainder
    warning_details = [
        line.rstrip() for line in section.splitlines() if line.strip()
    ]

summary = {
    "status": "PASSED" if tests > 0 and passed == tests else "FAILED",
    "framework": "pytest",
    "discovered": tests,
    "passed": passed,
    "failed": failures + errors,
    "errors": errors,
    "skipped": skipped,
    "flaky": 0,
    "unexecuted": 0,
    "duration_seconds": round(duration, 3),
    "warning_count": warning_count,
    "warning_details": warning_details,
    "tests": test_cases,
    "report": "backend-pytest.xml",
    "log": "backend-pytest.log",
}

summary_path.write_text(json.dumps(summary, indent=2) + "\n")
print(f"Backend Pytest: {passed}/{tests} PASSED")
print(f"Duration: {duration:.3f}s | Warnings: {warning_count}")

if len(test_cases) != tests:
    raise SystemExit("Pytest test-case inventory does not match JUnit discovery.")
if tests < 1 or passed != tests or failures or errors or skipped:
    raise SystemExit("Backend Pytest did not meet the 100% release requirement.")
PY_PYTEST_SUMMARY

  printf 'PASS: Backend Pytest release gate.\n'

}

run_e2e() {
  command -v npm >/dev/null 2>&1 || fail "npm is required."
  command -v python3 >/dev/null 2>&1 || fail "python3 is required."
  command -v curl >/dev/null 2>&1 || fail "curl is required."

  [[ -f "$ACTIVE_RUN" ]] || fail "No active candidate test run. Run ./scripts/build-deployment.sh first."

  local candidate_id candidate_sha run_dir api_pid nginx_pid runtime
  IFS=$'\t' read -r candidate_id candidate_sha run_dir api_pid nginx_pid runtime < <(
    python3 - "$ACTIVE_RUN" <<'PY_ACTIVE'
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
  local manifest="$candidate_dir/manifest.json"

  [[ -f "$candidate_zip" && -f "$manifest" && -f "$candidate_dir/SHA256SUMS" ]] || fail "Candidate package, manifest or checksum file is missing."
  [[ -d "$runtime" ]] || fail "Candidate runtime is missing."
  [[ -f "$run_dir/sessions.json" ]] || fail "Candidate E2E sessions are missing."
  [[ -f "$run_dir/secrets/jwt.secret" ]] || fail "Candidate runtime secret is missing."

  local actual_sha
  actual_sha="$(shasum -a 256 "$candidate_zip" | awk '{print $1}')"
  [[ "$actual_sha" == "$candidate_sha" ]] || fail "Candidate ZIP checksum differs from active test-run metadata."

  python3 - "$manifest" "$candidate_id" "$candidate_sha" "$candidate_zip" <<'PY_MANIFEST'
import json, sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
if data.get("candidate_id") != sys.argv[2]:
    raise SystemExit("Candidate manifest ID mismatch.")
if data.get("sha256") != sys.argv[3]:
    raise SystemExit("Candidate manifest checksum mismatch.")
if data.get("archive") != Path(sys.argv[4]).name:
    raise SystemExit("Candidate manifest archive filename mismatch.")

pytest = data.get("backend_pytest")
if not isinstance(pytest, dict) or pytest.get("status") != "PASSED":
    raise SystemExit("Candidate has no successful backend Pytest evidence.")
discovered = pytest.get("discovered")
if not isinstance(discovered, int) or discovered < 1:
    raise SystemExit("Backend Pytest discovery count is invalid.")
if pytest.get("passed") != discovered:
    raise SystemExit("Backend Pytest passed count does not match discovery.")
for key in ("failed", "errors", "skipped", "flaky", "unexecuted"):
    if pytest.get(key) != 0:
        raise SystemExit(f"Backend Pytest has nonzero {key} count.")
PY_MANIFEST

  (
    cd "$candidate_dir"
    shasum -a 256 -c SHA256SUMS
  ) || fail "Candidate SHA256SUMS verification failed."

  local status
  status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status",""))' "$ACTIVE_RUN")"
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
    python3 - "$ACTIVE_RUN" "$run_dir" "$candidate_id" "$candidate_sha" "$started_at" <<'PY_FAIL'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
active, run_dir, cid, sha, started = sys.argv[1:]
result = {
    "candidate_id": cid, "sha256": sha, "status": "FAILED",
    "failed_stage": "automated-e2e",
    "started_at": started,
    "completed_at": datetime.now(timezone.utc).isoformat(),
    "run_dir": run_dir,
}
Path(active).write_text(json.dumps(result, indent=2) + "\n")
Path(run_dir, "release-gate.json").write_text(json.dumps(result, indent=2) + "\n")
PY_FAIL
    fail "Automated E2E suite failed. Candidate is not eligible for promotion."
  fi

  if ! python3 "$ROOT/scripts/validate-e2e-report.py" \
    --report "$run_dir/reports/automated.json" \
    --output "$run_dir/reports/automated-summary.json"; then
    python3 - "$ACTIVE_RUN" "$run_dir" "$candidate_id" "$candidate_sha" "$started_at" <<'PY_FAIL'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
active, run_dir, cid, sha, started = sys.argv[1:]
result = {
    "candidate_id": cid, "sha256": sha, "status": "FAILED",
    "failed_stage": "automated-e2e-report-validation",
    "started_at": started,
    "completed_at": datetime.now(timezone.utc).isoformat(),
    "run_dir": run_dir,
}
Path(active).write_text(json.dumps(result, indent=2) + "\n")
Path(run_dir, "release-gate.json").write_text(json.dumps(result, indent=2) + "\n")
PY_FAIL
    fail "Automated E2E report did not satisfy release criteria."
  fi

  printf '\n== 2/2: Run visible real-email E2E test ==\n'
  printf 'Complete the email verification in the visible browser when prompted.\n'

  export FORGE_E2E_JSON_REPORT="$run_dir/reports/real-email.json"
  if ! (
    cd "$FRONTEND"
    npm run test:e2e:real-email
  ) 2>&1 | tee "$run_dir/logs/playwright-real-email.log"; then
    python3 - "$ACTIVE_RUN" "$run_dir" "$candidate_id" "$candidate_sha" "$started_at" <<'PY_FAIL'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
active, run_dir, cid, sha, started = sys.argv[1:]
result = {
    "candidate_id": cid, "sha256": sha, "status": "FAILED",
    "failed_stage": "real-email-e2e",
    "started_at": started,
    "completed_at": datetime.now(timezone.utc).isoformat(),
    "run_dir": run_dir,
}
Path(active).write_text(json.dumps(result, indent=2) + "\n")
Path(run_dir, "release-gate.json").write_text(json.dumps(result, indent=2) + "\n")
PY_FAIL
    fail "Real-email E2E test failed. Candidate is not eligible for promotion."
  fi

  if ! python3 "$ROOT/scripts/validate-e2e-report.py" \
    --report "$run_dir/reports/real-email.json" \
    --output "$run_dir/reports/real-email-summary.json"; then
    python3 - "$ACTIVE_RUN" "$run_dir" "$candidate_id" "$candidate_sha" "$started_at" <<'PY_FAIL'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
active, run_dir, cid, sha, started = sys.argv[1:]
result = {
    "candidate_id": cid, "sha256": sha, "status": "FAILED",
    "failed_stage": "real-email-e2e-report-validation",
    "started_at": started,
    "completed_at": datetime.now(timezone.utc).isoformat(),
    "run_dir": run_dir,
}
Path(active).write_text(json.dumps(result, indent=2) + "\n")
Path(run_dir, "release-gate.json").write_text(json.dumps(result, indent=2) + "\n")
PY_FAIL
    fail "Real-email E2E report did not satisfy release criteria."
  fi

  python3 - "$ACTIVE_RUN" "$run_dir" "$candidate_id" "$candidate_sha" "$started_at" <<'PY_PASS'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
active, run_dir, cid, sha, started = sys.argv[1:]
run = Path(run_dir)
automated = json.loads((run / "reports/automated-summary.json").read_text())
real_email = json.loads((run / "reports/real-email-summary.json").read_text())
manifest_path = Path(run_dir).parents[1] / "candidates" / cid / "manifest.json"
manifest = json.loads(manifest_path.read_text())
backend_pytest = manifest.get("backend_pytest")

if not isinstance(backend_pytest, dict) or backend_pytest.get("status") != "PASSED":
    raise SystemExit("Backend Pytest evidence is missing or has not passed.")

result = {
    "candidate_id": cid,
    "sha256": sha,
    "status": "PASSED",
    "started_at": started,
    "completed_at": datetime.now(timezone.utc).isoformat(),
    "automated_tests_expected": automated["discovered"],
    "automated_tests_status": "PASSED",
    "real_email_tests_expected": real_email["discovered"],
    "real_email_test_status": "PASSED",
    "backend_pytest": backend_pytest,
    "backend_pytest_status": "PASSED",
    "backend_pytest_expected": backend_pytest["discovered"],
    "automated_e2e": automated,
    "real_email_e2e": real_email,
    "real_email_completion": "User completed visible browser verification",
    "run_dir": run_dir,
    "evidence_dir": str(run / "evidence"),
}
Path(active).write_text(json.dumps(result, indent=2) + "\n")
(run / "release-gate.json").write_text(json.dumps(result, indent=2) + "\n")
PY_PASS

  if [[ "${FORGE_SKIP_OUTLOOK_DRAFT:-0}" == "1" ]]; then
    printf '\nOutlook draft creation skipped by FORGE_SKIP_OUTLOOK_DRAFT=1.\n'
  else
    printf '\nPreparing Outlook release draft...\n'
    if python3 "$ROOT/scripts/create-release-draft.py" --candidate-id "$candidate_id"; then
      printf 'Outlook draft preparation completed. Review it before sending.\n'
    else
      printf 'WARNING: Release gate passed, but Outlook draft preparation needs attention.\n' >&2
    fi
  fi

  printf '\nPASS: Both E2E stages completed.\n'
  printf 'Candidate %s is eligible for promotion.\n' "$candidate_id"
  printf 'Release evidence: %s\n' "$run_dir"
}

create_candidate_and_start() {
  mkdir -p "$CANDIDATES" "$TEST_RUNS"

  cleanup_previous_candidate_services

  for port in 18875 18876; do
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
      fail "Port $port is still in use after previous-candidate cleanup."
    fi
  done

  local git_commit candidate_id candidate_dir candidate_zip run_dir runtime
  git_commit="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || printf 'unknown')"
  candidate_id="$(date -u +%Y%m%dT%H%M%SZ)-$(printf '%s' "$git_commit" | cut -c1-8)-$(python3 -c 'import secrets; print(secrets.token_hex(3))')"

  candidate_dir="$CANDIDATES/$candidate_id"
  run_dir="$TEST_RUNS/$candidate_id"
  candidate_zip="$candidate_dir/FORGE-Deployment-${candidate_id}.zip"
  runtime="$run_dir/runtime/forge-deployment"

  [[ ! -e "$candidate_dir" ]] || fail "Candidate directory already exists: $candidate_dir"
  [[ ! -e "$run_dir" ]] || fail "Test-run directory already exists: $run_dir"

  mkdir -p "$candidate_dir" "$run_dir/runtime" "$run_dir/logs" \
    "$run_dir/evidence" "$run_dir/secrets"

  cp "$OUTPUT/backend-pytest.xml" "$run_dir/evidence/backend-pytest.xml"
  cp "$OUTPUT/backend-pytest.log" "$run_dir/evidence/backend-pytest.log"
  cp "$OUTPUT/backend-pytest-summary.json" "$run_dir/evidence/backend-pytest-summary.json"

  cp "$ZIP" "$candidate_zip"
  local candidate_sha
  candidate_sha="$(shasum -a 256 "$candidate_zip" | awk '{print $1}')"

  printf '%s  %s\n' "$candidate_sha" "$(basename "$candidate_zip")" > "$candidate_dir/SHA256SUMS"

  python3 - "$candidate_dir/manifest.json" "$candidate_id" "$candidate_sha" "$candidate_zip" "$git_commit" "$OUTPUT/backend-pytest-summary.json" <<'PY_MANIFEST'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

manifest, cid, sha, archive, commit, pytest_path = sys.argv[1:]
p = Path(archive)
pytest = json.loads(Path(pytest_path).read_text())

if pytest.get("status") != "PASSED":
    raise SystemExit("Cannot create candidate: backend Pytest did not pass.")
discovered = pytest.get("discovered")
if not isinstance(discovered, int) or discovered < 1:
    raise SystemExit("Invalid backend Pytest discovery count.")
if pytest.get("passed") != discovered:
    raise SystemExit("Backend Pytest passed count does not match discovery.")
for key in ("failed", "errors", "skipped", "flaky", "unexecuted"):
    if pytest.get(key) != 0:
        raise SystemExit(f"Backend Pytest {key} count is nonzero.")

data = {
    "candidate_id": cid,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "git_commit": commit,
    "archive": p.name,
    "sha256": sha,
    "size_bytes": p.stat().st_size,
    "backend_pytest": pytest,
}
Path(manifest).write_text(json.dumps(data, indent=2) + "\n")
PY_MANIFEST

  chmod 0444 "$candidate_zip" "$candidate_dir/manifest.json" "$candidate_dir/SHA256SUMS"

  printf '\nCandidate created: %s\n' "$candidate_id"
  printf 'Verifying immutable candidate archive...\n'
  actual_sha="$(shasum -a 256 "$candidate_zip" | awk '{print $1}')"
  [[ "$actual_sha" == "$candidate_sha" ]] || fail "Candidate checksum changed during creation."

  /usr/bin/unzip -q "$candidate_zip" -d "$run_dir/runtime"
  [[ -f "$runtime/backend/api/app/main.py" ]] || fail "Extracted candidate API is missing."
  [[ -f "$runtime/frontend/index.html" ]] || fail "Extracted candidate frontend is missing."

  printf '\n== Prepare isolated candidate runtime ==\n'

  python3 - "$ROOT/backend/api/config/email.json" \
    "$runtime/backend/api/config" <<'PY_OVERLAY'
import json, sys
from pathlib import Path

email_source, runtime_config = map(Path, sys.argv[1:])
runtime_config.mkdir(parents=True, exist_ok=True)

email = json.loads(email_source.read_text())
smtp = email.get("smtp", {})

if not smtp.get("host") or not smtp.get("port") or not smtp.get("sender"):
    raise SystemExit("Local SMTP host, port and sender must be configured.")

if smtp.get("username"):
    raise SystemExit("Unexpected SMTP username. Review local E2E SMTP configuration.")

if any(k.lower() in {"password", "passwd", "secret", "api_key"} for k in smtp):
    raise SystemExit("SMTP credentials must not be copied into the E2E runtime.")

email.setdefault("magic_link", {})["frontend_base_url"] = "http://127.0.0.1:18876"
(runtime_config / "email.json").write_text(json.dumps(email, indent=2) + "\n")
PY_OVERLAY

  chmod 0600 "$runtime/backend/api/config/email.json"
  check_corporate_ollama "$runtime/backend/api/config/ai.json" "$run_dir/logs"

  python3 - "$run_dir/secrets/jwt.secret" <<'PY_SECRET'
import secrets, sys
from pathlib import Path
p = Path(sys.argv[1])
p.write_text(secrets.token_urlsafe(48) + "\n")
p.chmod(0o600)
PY_SECRET

  printf 'Installing locked dependencies from extracted candidate...\n'
  (
    cd "$runtime"
    unset VIRTUAL_ENV
    uv sync --locked --no-dev --no-group experiments
  ) 2>&1 | tee "$run_dir/logs/uv-sync.log"

  [[ -x "$runtime/.venv/bin/python" ]] || fail "Candidate virtual environment was not created."

  export FORGE_JWT_SECRET
  FORGE_JWT_SECRET="$(tr -d '\r\n' < "$run_dir/secrets/jwt.secret")"

  printf '\nCreating owner, contributor and viewer sessions...\n'
  (
    cd "$ROOT"
    "$runtime/.venv/bin/python" "$ROOT/scripts/e2e/create_sessions.py" \
      "$runtime/backend/api" "$run_dir/sessions.json"
  ) 2>&1 | tee "$run_dir/logs/session-creation.log"

  [[ -s "$run_dir/sessions.json" ]] || fail "E2E session file was not created."

  local api_pid="" nginx_pid=""

  cleanup_candidate_services() {
    if [[ -n "$nginx_pid" ]]; then
      kill "$nginx_pid" 2>/dev/null || true
      wait "$nginx_pid" 2>/dev/null || true
    fi
    if [[ -n "$api_pid" ]]; then
      kill "$api_pid" 2>/dev/null || true
      wait "$api_pid" 2>/dev/null || true
    fi
  }

  trap cleanup_candidate_services EXIT
  trap 'exit 130' INT TERM

  printf '\nStarting candidate API on port 18875...\n'
  (
    cd "$runtime/backend/api"
    export FORGE_JWT_SECRET
    export FORGE_FRONTEND_BASE_URL="http://127.0.0.1:18876"
    exec "$runtime/.venv/bin/python" -m uvicorn app.main:app \
      --host 127.0.0.1 --port 18875
  ) > "$run_dir/logs/api.log" 2>&1 &
  api_pid=$!

  local nginx_prefix="$run_dir/nginx"
  mkdir -p "$nginx_prefix/logs"

  cat > "$nginx_prefix/nginx.conf" <<NGINX
worker_processes 1;
pid $nginx_prefix/logs/nginx.pid;
error_log $nginx_prefix/logs/error.log;
events { worker_connections 256; }
http {
  access_log $nginx_prefix/logs/access.log;
  types {
    text/html html htm;
    text/css css;
    application/javascript js mjs;
    application/json json map;
    image/svg+xml svg svgz;
    image/png png;
    image/jpeg jpg jpeg;
    image/gif gif;
    image/webp webp;
    image/x-icon ico;
    font/woff woff;
    font/woff2 woff2;
    application/wasm wasm;
  }
  default_type application/octet-stream;
  server {
    listen 127.0.0.1:18876;
    server_name localhost;
    root $runtime/frontend;
    index index.html;
    location /api/ {
      proxy_pass http://127.0.0.1:18875;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
    }
    location = /health {
      proxy_pass http://127.0.0.1:18875/health;
      proxy_set_header Host \$host;
    }
    location / {
      try_files \$uri \$uri/ /index.html;
    }
  }
}
NGINX

  nginx -t -p "$nginx_prefix/" -c "$nginx_prefix/nginx.conf" \
    || fail "Candidate Nginx configuration failed validation."

  nginx -p "$nginx_prefix/" -c "$nginx_prefix/nginx.conf" -g 'daemon off;' \
    > "$run_dir/logs/nginx-console.log" 2>&1 &
  nginx_pid=$!

  local api_ready=0 ui_ready=0
  for attempt in $(seq 1 45); do
    if curl --silent --fail http://127.0.0.1:18875/health >/dev/null 2>&1; then
      api_ready=1
      break
    fi
    if ! kill -0 "$api_pid" 2>/dev/null; then
      cat "$run_dir/logs/api.log" >&2 || true
      fail "Candidate API exited during startup."
    fi
    sleep 1
  done
  [[ "$api_ready" -eq 1 ]] || fail "Candidate API did not become healthy."

  for attempt in $(seq 1 20); do
    if curl --silent --fail http://127.0.0.1:18876/ | grep -q '<html'; then
      ui_ready=1
      break
    fi
    if ! kill -0 "$nginx_pid" 2>/dev/null; then
      cat "$run_dir/logs/nginx-console.log" >&2 || true
      fail "Candidate Nginx exited during startup."
    fi
    sleep 1
  done
  [[ "$ui_ready" -eq 1 ]] || fail "Candidate frontend did not become healthy."

  curl --silent --fail http://127.0.0.1:18876/health >/dev/null \
    || fail "Candidate Nginx health proxy failed."

  python3 - "$run_dir/runtime-processes.json" "$candidate_id" "$run_dir" \
    "$runtime" "$api_pid" "$nginx_pid" <<'PY_PROCESS_METADATA'
import json, os, sys
from pathlib import Path

metadata_path, cid, run_dir, runtime, api_pid, nginx_pid = sys.argv[1:]
data = {
    "candidate_id": cid,
    "run_dir": str(Path(run_dir).resolve()),
    "runtime": str(Path(runtime).resolve()),
    "api_pid": int(api_pid),
    "nginx_pid": int(nginx_pid),
    "api_port": 18875,
    "nginx_port": 18876,
}
path = Path(metadata_path)
tmp = path.with_suffix(".tmp")
tmp.write_text(json.dumps(data, indent=2) + "\n")
os.chmod(tmp, 0o600)
tmp.replace(path)
PY_PROCESS_METADATA

  python3 - "$ACTIVE_RUN" "$candidate_id" "$candidate_sha" "$run_dir" \
    "$runtime" "$api_pid" "$nginx_pid" <<'PY_ACTIVE'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
active, cid, sha, run_dir, runtime, api_pid, nginx_pid = sys.argv[1:]
data = {
    "candidate_id": cid,
    "sha256": sha,
    "status": "PREPARED",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "run_dir": run_dir,
    "runtime": runtime,
    "api_pid": int(api_pid),
    "nginx_pid": int(nginx_pid),
    "api_url": "http://127.0.0.1:18875",
    "ui_url": "http://127.0.0.1:18876",
}
p = Path(active)
p.parent.mkdir(parents=True, exist_ok=True)
tmp = p.with_suffix(".tmp")
tmp.write_text(json.dumps(data, indent=2) + "\n")
tmp.replace(p)
PY_ACTIVE

  chmod 0600 "$ACTIVE_RUN"

  if [[ "$PREPARE_ONLY" -eq 1 ]]; then
    printf '\n%s\n' '============================================================'
    printf 'FORGE candidate runtime is READY (prepare-only mode)\n'
    printf 'Candidate: %s\n' "$candidate_id"
    printf 'API: http://127.0.0.1:18875/health\n'
    printf 'UI:  http://127.0.0.1:18876\n'
    printf 'Sessions: %s/sessions.json\n' "$run_dir"
    printf 'Evidence: %s/evidence\n' "$run_dir"
    printf '\nRun WP-02 using the isolated Playwright configuration.\n'
    printf 'The candidate services will remain running.\n'
    printf '%s\n' '============================================================'

    trap - EXIT INT TERM
    return 0
  fi

  printf '\n%s\n' '============================================================'
  printf 'FORGE candidate runtime is READY\n'
  printf 'Candidate: %s\n' "$candidate_id"
  printf 'SHA-256: %s\n' "$candidate_sha"
  printf 'API: http://127.0.0.1:18875/health\n'
  printf 'UI:  http://127.0.0.1:18876\n'
  printf '\nLaunching E2E automatically in a new Terminal window...\n'

  rm -f "$run_dir/e2e-process.exit"

  if ! osascript - "$ROOT" "$run_dir" <<'APPLESCRIPT'
on run argv
    set repoRoot to item 1 of argv
    set runDir to item 2 of argv
    set exitFile to runDir & "/e2e-process.exit"

    set shellCommand to "cd " & quoted form of repoRoot & " && if ./scripts/build-deployment.sh --e2e; then /usr/bin/printf '0' > " & quoted form of exitFile & "; echo 'FORGE E2E completed successfully.'; else /usr/bin/printf '1' > " & quoted form of exitFile & "; echo 'FORGE E2E failed. Review the candidate test-run logs.'; fi"

    tell application "Terminal"
        activate
        do script shellCommand
    end tell
end run
APPLESCRIPT
  then
    fail "Could not launch E2E in a new Terminal window."
  fi

  printf 'E2E launched automatically in the new Terminal window.\n'
  printf 'This terminal will stop the isolated services after E2E finishes.\n'
  printf '%s\n' '============================================================'

  while true; do
    if [[ -f "$run_dir/e2e-process.exit" ]]; then
      e2e_exit="$(tr -d '[:space:]' < "$run_dir/e2e-process.exit")"

      if [[ "$e2e_exit" == "0" ]]; then
        printf '\nE2E completed successfully. Stopping isolated services...\n'
        break
      fi

      fail "E2E finished with failure. Review $run_dir/logs and release-gate.json."
    fi

    if ! kill -0 "$api_pid" 2>/dev/null; then
      printf '\nERROR: Candidate API stopped unexpectedly. See %s\n' "$run_dir/logs/api.log" >&2
      exit 1
    fi

    if ! kill -0 "$nginx_pid" 2>/dev/null; then
      printf '\nERROR: Candidate Nginx stopped unexpectedly. See %s\n' "$run_dir/logs/nginx-console.log" >&2
      exit 1
    fi

    sleep 2
  done
}

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

command -v npm >/dev/null 2>&1 || fail "npm is required to build the Angular production frontend."
command -v uv >/dev/null 2>&1 || fail "uv is required to install locked Python dependencies and smoke-test the staged backend."
command -v python3 >/dev/null 2>&1 || fail "python3 is required."
command -v curl >/dev/null 2>&1 || fail "curl is required for the local health check."

for required in \
  "$ROOT/pyproject.toml" "$ROOT/uv.lock" "$ROOT/.python-version" \
  "$ROOT/backend/api/app" "$ROOT/backend/api/config/ai.json" \
  "$ROOT/backend/api/config/email.json" "$ROOT/backend/api/config/authentication.json"; do
  [[ -e "$required" ]] || fail "Required source/config not found: ${required#"$ROOT"/}"
done

[[ "$(tr -d '[:space:]' < "$ROOT/.python-version")" == "3.11" ]] || fail "Expected .python-version to contain 3.11."

# Clean generated outputs before every deployment rebuild.
# These paths are restricted to this repository.
[[ "$OUTPUT" == "$ROOT/dist" ]] || {
  printf 'ERROR: Unexpected deployment output path: %s\n' "$OUTPUT" >&2
  exit 1
}
[[ "$FRONTEND" == "$ROOT/frontend" ]] || {
  printf 'ERROR: Unexpected frontend path: %s\n' "$FRONTEND" >&2
  exit 1
}

printf '\n== Clean previous build outputs ==\n'
rm -rf -- "$STAGE" "$ZIP" "$TEST_LOG" "$FRONTEND/dist"
mkdir -p "$OUTPUT"
rm -f "$OUTPUT/backend-pytest.log" "$OUTPUT/backend-pytest.xml" "$OUTPUT/backend-pytest-summary.json"

run_backend_pytest

printf '\n== 1/5: Build Angular production frontend ==\n'
(
  cd "$FRONTEND"
  npm ci
  npm run build
)

BROWSER="$FRONTEND/dist/forge-ui/browser"
[[ -f "$BROWSER/index.html" ]] || fail "Angular build did not produce frontend/dist/forge-ui/browser/index.html."

printf '\n== 2/5: Stage a clean deployment bundle ==\n'
rm -rf "$STAGE" "$ZIP"
mkdir -p "$STAGE/backend/api" "$STAGE/frontend" "$STAGE/deployment"

cp "$ROOT/pyproject.toml" "$ROOT/uv.lock" "$ROOT/.python-version" "$STAGE/"
[[ ! -f "$ROOT/LICENSE" ]] || cp "$ROOT/LICENSE" "$STAGE/"
cp -R "$ROOT/backend/api/app" "$STAGE/backend/api/app"
mkdir -p "$STAGE/backend/api/config" "$STAGE/backend/api/data"
cp -R "$BROWSER"/. "$STAGE/frontend"/

# Package sanitized, host-configurable settings. Never copy the local auth secret,
# SMTP username/password, or local runtime JSON data.
# Deployment-only AI overrides. Source ai.json remains unchanged.
DEPLOY_AI_BASE_URL="${FORGE_DEPLOY_AI_BASE_URL:-http://10.254.231.222:11434}"
DEPLOY_AI_MODEL="${FORGE_DEPLOY_AI_MODEL:-gemma4-jfrog-Q4:1.0}"

python3 - "$ROOT" "$STAGE" "$DEPLOY_AI_BASE_URL" "$DEPLOY_AI_MODEL" <<'PY'
import json, os, sys
from pathlib import Path
source = Path(sys.argv[1])
stage = Path(sys.argv[2])
deploy_ai_base_url = sys.argv[3]
deploy_ai_model = sys.argv[4]
src_cfg = source / "backend/api/config"
dst_cfg = stage / "backend/api/config"

def load(name):
    with (src_cfg / name).open(encoding="utf-8") as f:
        return json.load(f)

ai = load("ai.json")
# Apply deployment settings only to the staged configuration.
ai["base_url"] = deploy_ai_base_url
ai["model"] = deploy_ai_model

email = load("email.json")
auth = load("authentication.json")

smtp = email.setdefault("smtp", {})
smtp["host"] = "REPLACE_WITH_APPROVED_SMTP_HOST"
smtp["sender"] = "REPLACE_WITH_APPROVED_SENDER"
smtp["username"] = ""
for key in list(smtp):
    if key.lower() in {"password", "passwd", "secret", "api_key"}:
        smtp.pop(key)
email.setdefault("magic_link", {})["frontend_base_url"] = os.environ.get(
    "FORGE_FRONTEND_BASE_URL",
    "https://REPLACE-WITH-FORGE-HOST",
).strip().rstrip("/")

token = auth.get("development_token", {})
if not email["magic_link"]["frontend_base_url"].startswith(("http://", "https://")):
    raise SystemExit("ERROR: FORGE_FRONTEND_BASE_URL must be an HTTP(S) URL.")


sanitized_auth = {
    "allowed_domains": auth.get("allowed_domains", []),
    "development_token": {
        "algorithm": token.get("algorithm", "HS256"),
        "expiration_minutes": token.get("expiration_minutes", 60),
    },
}
for name, obj in (("ai.json", ai), ("email.json", email), ("authentication.json", sanitized_auth)):
    (dst_cfg / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

# SMTP settings remain sanitized in the deployment package.


cat > "$STAGE/README-DEPLOYMENT.md" <<'README'
# FORGE Deployment Bundle

This bundle contains the compiled Angular frontend, FastAPI application source,
the repository's locked Python dependency definitions and deployment configuration.
It does not contain `.git`, `node_modules`, virtual environments, local runtime JSON
data, or your development authentication secret.

## Contents
- `frontend/` — compiled Angular browser application; Node.js is not needed to serve it.
- `backend/api/app/` — FastAPI application, templates and assets.
- `backend/api/config/` — sanitized application configuration. Configure approved SMTP settings on the target host.
- `pyproject.toml`, `uv.lock`, `.python-version` — locked Python environment definition.
- `deployment/` — notes about the local smoke test and server handoff.

## Python prerequisites and install
Install approved Python 3.11 and `uv` on the target host, then run from this bundle's root:

```sh
uv sync --locked --no-dev --no-group experiments
```

The API application must be launched with `backend/api` as its working directory, for example:

```sh
# macOS/Linux example
../../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Windows PowerShell example
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Adjust the relative path to `.venv` if your organization chooses a different environment location.
Check `http://127.0.0.1:8000/health` locally on the host after starting the API.

## Configuration required before use
Review `backend/api/config/ai.json`, `email.json`, and `authentication.json`:
- The build sets the deployment Ollama endpoint and model in `ai.json`.
  Defaults: `http://10.254.231.222:11434` and `gemma4-jfrog-Q4:1.0`.
  Override them with `FORGE_DEPLOY_AI_BASE_URL` and `FORGE_DEPLOY_AI_MODEL`
  when running the build for another deployment environment.
- Verify `email.json` contains the approved SMTP settings for this deployment.
- Configure `FORGE_FRONTEND_BASE_URL` in the API process environment to the browser-accessible FORGE base URL. This overrides `email.json` without changing SMTP settings.
- For example, use `http://127.0.0.1:18766` for the local extracted test launcher, or the approved HTTPS URL for a hosted deployment.
- Set `FORGE_JWT_SECRET` in the API process environment to a securely generated secret of at least 32 bytes. Never store it in JSON or the deployment ZIP. Confirm `allowed_domains` with the application owner.
- If SMTP authentication is required, provide `FORGE_SMTP_PASSWORD` through the approved secret/environment mechanism. Do not put SMTP passwords in JSON or ZIP files.
- Ensure the host can reach the corporate profile API over HTTPS and trusts the corporate certificate chain.

The deployment ZIP contains no JWT signing secret or SMTP password. Supply `FORGE_JWT_SECRET` through the target host's approved secret mechanism. Configure SMTP settings and `FORGE_FRONTEND_BASE_URL` for the target environment.

## Nginx reference configuration
`deployment/nginx.conf.template` provides a server block to serve the Angular frontend, proxy `/api/` and `/health` to FastAPI, and fall back to `index.html` for Angular routes. Replace its `root` path with the absolute target path and integrate it with the installed Nginx configuration. The build command tests this route locally if Nginx is installed on the Mac.

## Server hosting
The worker should confirm the approved hosting method and target paths with IT. The API binds to loopback in the example above; serve the UI and proxy `/api/*` and `/health` through the organization's approved reverse proxy/web server. Preserve those paths and configure SPA fallback to `index.html`. Do not expose port 8000 directly to the network.

This bundle does not assume a Windows service manager, hostname, or firewall rules. Runtime data is not included; arrange the approved data migration separately.
README

cat > "$STAGE/deployment/nginx.conf.template" <<'NGINX'
# Reference Nginx server block. Replace root with the absolute frontend path and
# integrate this server block into the target host's Nginx configuration.
server {
    # Explicit MIME types are required for Angular ES module scripts.
    types {
        text/html html htm;
        text/css css;
        application/javascript js mjs;
        application/json json map;
        image/svg+xml svg svgz;
        image/png png;
        image/jpeg jpg jpeg;
        image/gif gif;
        image/webp webp;
        image/x-icon ico;
        font/woff woff;
        font/woff2 woff2;
        application/wasm wasm;
    }
    default_type application/octet-stream;

    listen 8080;
    server_name _;
    root /ABSOLUTE/PATH/TO/forge-deployment/frontend;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX

cat > "$STAGE/deployment/LOCAL-SMOKE-TEST.md" <<'README'
# Local staging smoke test

The release builder installs locked runtime dependencies into a temporary `.venv`
inside the staged bundle and starts FastAPI. If Nginx is installed on the build Mac,
it also starts a temporary Nginx instance and checks the Angular entry page and the
proxied `/health` endpoint. Temporary runtime files are removed before ZIP creation.
README

printf '\n== 3/5: Install locked runtime dependencies into staged bundle ==\n'
(
  cd "$STAGE"
  uv sync --locked --no-dev --no-group experiments
) 2>&1 | tee "$TEST_LOG"

printf '\n== 4/5: Smoke-test staged backend and optional Nginx ==\n'
(
  export FORGE_JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  cd "$STAGE/backend/api"
  "$STAGE/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 18765 \
    > "$OUTPUT/forge-deployment-api.log" 2>&1 &
  API_PID=$!
  NGINX_PREFIX=""
  cleanup() {
    if [[ -n "$NGINX_PREFIX" ]] && command -v nginx >/dev/null 2>&1; then
      nginx -p "$NGINX_PREFIX/" -c "$NGINX_PREFIX/nginx.conf" -s quit >/dev/null 2>&1 || true
    fi
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" >/dev/null 2>&1 || true
  }
  trap cleanup EXIT

  READY=0
  for attempt in $(seq 1 30); do
    if curl --silent --show-error --fail http://127.0.0.1:18765/health >/dev/null 2>&1; then
      READY=1
      break
    fi
    sleep 1
  done
  if [[ "$READY" -ne 1 ]]; then
    cat "$OUTPUT/forge-deployment-api.log" >&2 || true
    fail "Staged backend did not return a healthy response. See dist/forge-deployment-api.log."
  fi
  printf 'Staged backend health check: PASS\n'

  if command -v nginx >/dev/null 2>&1; then
    NGINX_PREFIX="$(mktemp -d "$OUTPUT/nginx-smoke.XXXXXX")"
    mkdir -p "$NGINX_PREFIX/logs"
    cat > "$NGINX_PREFIX/nginx.conf" <<NGINX
worker_processes 1;
pid $NGINX_PREFIX/logs/nginx.pid;
error_log $NGINX_PREFIX/logs/error.log;
events { worker_connections 128; }
http {
  access_log $NGINX_PREFIX/logs/access.log;
  types {
    text/html html;
    text/css css;
    application/javascript js;
    application/json json;
    image/svg+xml svg;
    image/x-icon ico;
  }
  default_type application/octet-stream;
  server {
    listen 127.0.0.1:18766;
    server_name localhost;
    root $STAGE/frontend;
    index index.html;
    location /api/ {
      proxy_pass http://127.0.0.1:18765;
      proxy_set_header Host \$host;
      proxy_set_header X-Real-IP \$remote_addr;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto \$scheme;
    }
    location = /health {
      proxy_pass http://127.0.0.1:18765/health;
      proxy_set_header Host \$host;
    }
    location / {
      try_files \$uri \$uri/ /index.html;
    }
  }
}
NGINX
    if ! nginx -t -p "$NGINX_PREFIX/" -c "$NGINX_PREFIX/nginx.conf" >/dev/null 2>&1; then
      cat "$NGINX_PREFIX/logs/error.log" >&2 || true
      fail "Nginx configuration validation failed."
    fi
    nginx -p "$NGINX_PREFIX/" -c "$NGINX_PREFIX/nginx.conf"
    FRONTEND_OK=0
    for attempt in $(seq 1 15); do
      if curl --silent --show-error --fail http://127.0.0.1:18766/ | grep -q '<html'; then FRONTEND_OK=1; break; fi
      sleep 1
    done
    [[ "$FRONTEND_OK" -eq 1 ]] || fail "Nginx did not serve the Angular index page."
    curl --silent --show-error --fail http://127.0.0.1:18766/health >/dev/null || fail "Nginx health proxy failed."
    printf 'Nginx config validation: PASS\n'
    printf 'Nginx frontend serving: PASS\n'
    printf 'Nginx -> FastAPI /health proxy: PASS\n'
  else
    printf 'Nginx smoke test: SKIPPED (nginx is not installed on this Mac).\n'
    printf 'Install Nginx and rerun to test the proxy path locally.\n'
  fi
)
rm -rf "$OUTPUT"/nginx-smoke.* 2>/dev/null || true

printf '\n== 5/5: Remove temporary environment and create ZIP ==\n'
rm -rf "$STAGE/.venv"
# Defensive cleanup: never ship caches or local data by accident.
find "$STAGE" -name '.DS_Store' -delete
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$STAGE" -name '*.pyc' -delete

# Remove runtime data created by smoke tests. Preserve the source repository.
find "$STAGE/backend/api/data" -mindepth 1 -maxdepth 1 \
  ! -name '.gitkeep' -exec rm -rf {} +
touch "$STAGE/backend/api/data/.gitkeep"

# Fail closed if any top-level runtime JSON remains in the staged bundle.
UNEXPECTED_DATA="$(
  find "$STAGE/backend/api/data" -mindepth 1 -maxdepth 1 \
    -type f -name '*.json' -print -quit
)"
if [[ -n "$UNEXPECTED_DATA" ]]; then
  printf 'ERROR: Runtime data must not be packaged: %s\\n' "$UNEXPECTED_DATA" >&2
  exit 1
fi

rm -f "$ZIP"
(
  cd "$OUTPUT"
  /usr/bin/zip -qr "$(basename "$ZIP")" "$(basename "$STAGE")"
)

# Verify the archive itself, not just the staging directory.
if /usr/bin/unzip -Z1 "$ZIP" | grep -Eq '^forge-deployment/backend/api/data/[^/]+\.json$'; then
  printf 'ERROR: Runtime JSON data detected in deployment ZIP.\\n' >&2
  exit 1
fi

python3 - "$ZIP" <<'PY_VERIFY'
import json
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    auth_path = "forge-deployment/backend/api/config/authentication.json"
    email_path = "forge-deployment/backend/api/config/email.json"

    try:
        auth = json.loads(archive.read(auth_path))
        email = json.loads(archive.read(email_path))
    except KeyError as exc:
        raise SystemExit(f"ERROR: Required configuration missing from ZIP: {exc}")

    token = auth.get("development_token", {})
    if "secret" in token:
        raise SystemExit("ERROR: JWT signing secret detected in deployment ZIP.")

    smtp = email.get("smtp", {})
    sensitive_keys = {"password", "passwd", "secret", "api_key"}
    if any(key.lower() in sensitive_keys for key in smtp):
        raise SystemExit("ERROR: SMTP credential field detected in deployment ZIP.")

    if smtp.get("username") != "":
        raise SystemExit("ERROR: SMTP username was not sanitized.")
    if smtp.get("host") != "REPLACE_WITH_APPROVED_SMTP_HOST":
        raise SystemExit("ERROR: SMTP host was not sanitized.")
    if smtp.get("sender") != "REPLACE_WITH_APPROVED_SENDER":
        raise SystemExit("ERROR: SMTP sender was not sanitized.")

print("Archive authentication secret check: PASS")
print("Archive SMTP sanitization check: PASS")
PY_VERIFY

printf '\n== Candidate creation and isolated E2E runtime ==\n'
printf 'Verified deployment ZIP: %s\n' "$ZIP"
printf 'Bundle size: %s\n' "$(du -h "$ZIP" | awk '{print $1}')"
printf 'Smoke-test log: %s\n' "$TEST_LOG"

create_candidate_and_start
