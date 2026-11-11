#!/usr/bin/env bash
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
  [[ -f "$ACTIVE_RUN" ]] || return 0

  local previous_run_dir
  previous_run_dir="$(
    python3 - "$ACTIVE_RUN" <<'PY_ACTIVE_CLEANUP'
import json, sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
print(data.get("run_dir", ""))
PY_ACTIVE_CLEANUP
  )"

  [[ -n "$previous_run_dir" ]] || return 0

  case "$previous_run_dir" in
    "$TEST_RUNS"/*) ;;
    *) fail "Previous run directory is outside the FORGE test-runs directory: $previous_run_dir" ;;
  esac

  local cleanup_pids="" port pid ppid command parent_command
  local remaining=0

  printf '\nChecking for services from the previous FORGE candidate...\n'

  for port in 18875 18876; do
    for pid in $(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true); do
      command="$(ps -ww -p "$pid" -o command= 2>/dev/null || true)"

      if [[ "$port" == "18875" ]]; then
        if [[ "$command" == *"$previous_run_dir"* &&
              "$command" == *"uvicorn app.main:app"* &&
              "$command" == *"--port 18875"* ]]; then
          cleanup_pids="$cleanup_pids $pid"
          printf 'Verified previous FORGE API: PID %s\n' "$pid"
        else
          fail "Port $port is occupied by an unverified process (PID $pid). Nothing was terminated."
        fi
      else
        if [[ "$command" == *"$previous_run_dir/nginx/"* &&
              "$command" == *"nginx: master process"* ]]; then
          cleanup_pids="$cleanup_pids $pid"
          printf 'Verified previous FORGE Nginx master: PID %s\n' "$pid"
        elif [[ "$command" == *"nginx: worker process"* ]]; then
          ppid="$(ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ')"
          parent_command="$(ps -ww -p "$ppid" -o command= 2>/dev/null || true)"

          if [[ "$parent_command" == *"$previous_run_dir/nginx/"* &&
                "$parent_command" == *"nginx: master process"* ]]; then
            case " $cleanup_pids " in
              *" $ppid "*) ;;
              *) cleanup_pids="$cleanup_pids $ppid" ;;
            esac
            printf 'Verified previous FORGE Nginx master via worker PID %s: master PID %s\n' "$pid" "$ppid"
          else
            fail "Port $port has an unverified Nginx worker (PID $pid). Nothing was terminated."
          fi
        else
          fail "Port $port is occupied by an unverified process (PID $pid). Nothing was terminated."
        fi
      fi
    done
  done

  if [[ -z "${cleanup_pids// /}" ]]; then
    printf 'No previous FORGE candidate services are running.\n'
    return 0
  fi

  for pid in $cleanup_pids; do
    command="$(ps -ww -p "$pid" -o command= 2>/dev/null || true)"
    [[ "$command" == *"$previous_run_dir"* ]] \
      || fail "Process PID $pid changed identity before cleanup. Stopping safely."
    kill -TERM "$pid" 2>/dev/null || true
  done

  printf 'Waiting for previous candidate services to stop...\n'

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
      fail "Port $port did not close after graceful FORGE service shutdown."
    fi
  done

  printf 'PASS: Previous FORGE services stopped. Ports 18875 and 18876 are free.\n'
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

  mkdir -p "$run_dir/logs" "$run_dir/evidence"
  check_corporate_ollama "$runtime/backend/api/config/ai.json" "$run_dir/logs"

  export FORGE_E2E_BASE_URL="http://127.0.0.1:18876"
  export FORGE_E2E_SESSIONS_FILE="$run_dir/sessions.json"
  export FORGE_E2E_EVIDENCE_DIR="$run_dir/evidence"
  export FORGE_E2E_CANDIDATE_ID="$candidate_id"

  printf '\nCandidate: %s\n' "$candidate_id"
  printf 'SHA-256: %s\n' "$candidate_sha"
  printf 'Runtime: %s\n' "$runtime"
  printf 'UI: %s\n' "$FORGE_E2E_BASE_URL"
  printf '\nVerifying Playwright test discovery...\n'

  local full_count email_count
  full_count="$(
    cd "$FRONTEND"
    npx playwright test --config=playwright.e2e-isolated.config.ts \
      --grep-invert 'REAL EMAIL E2E' --list |
      grep -c ' › ' || true
  )"
  email_count="$(
    cd "$FRONTEND"
    npx playwright test --config=playwright.e2e-isolated.config.ts \
      --project=real-email --list |
      grep -c ' › ' || true
  )"

  [[ "$full_count" -eq 56 ]] || fail "Expected 56 automated tests; discovered $full_count."
  [[ "$email_count" -eq 1 ]] || fail "Expected one real-email test; discovered $email_count."

  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  printf '\n== 1/2: Run 56 automated E2E tests ==\n'
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

  printf '\n== 2/2: Run visible real-email E2E test ==\n'
  printf 'Complete the email verification in the visible browser when prompted.\n'

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

  python3 - "$ACTIVE_RUN" "$run_dir" "$candidate_id" "$candidate_sha" "$started_at" <<'PY_PASS'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
active, run_dir, cid, sha, started = sys.argv[1:]
result = {
    "candidate_id": cid,
    "sha256": sha,
    "status": "PASSED",
    "started_at": started,
    "completed_at": datetime.now(timezone.utc).isoformat(),
    "automated_tests_expected": 56,
    "automated_tests_status": "PASSED",
    "real_email_tests_expected": 1,
    "real_email_test_status": "PASSED",
    "real_email_completion": "User completed visible browser verification",
    "run_dir": run_dir,
    "evidence_dir": str(Path(run_dir) / "evidence"),
}
Path(active).write_text(json.dumps(result, indent=2) + "\n")
Path(run_dir, "release-gate.json").write_text(json.dumps(result, indent=2) + "\n")
PY_PASS

  printf '\nPreparing Outlook release draft...\n'
  if python3 "$ROOT/scripts/create-release-draft.py" --candidate-id "$candidate_id"; then
    printf 'Outlook draft preparation completed. Review it before sending.\n'
  else
    printf 'WARNING: Release gate passed, but Outlook draft preparation needs attention.\n' >&2
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

  cp "$ZIP" "$candidate_zip"
  local candidate_sha
  candidate_sha="$(shasum -a 256 "$candidate_zip" | awk '{print $1}')"

  printf '%s  %s\n' "$candidate_sha" "$(basename "$candidate_zip")" > "$candidate_dir/SHA256SUMS"

  python3 - "$candidate_dir/manifest.json" "$candidate_id" "$candidate_sha" "$candidate_zip" "$git_commit" <<'PY_MANIFEST'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
manifest, cid, sha, archive, commit = sys.argv[1:]
p = Path(archive)
data = {
    "candidate_id": cid,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "git_commit": commit,
    "archive": p.name,
    "sha256": sha,
    "size_bytes": p.stat().st_size,
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
  "--e2e")
    [[ "$#" -eq 1 ]] || fail "Usage: $0 [--e2e]"
    run_e2e
    exit 0
    ;;
  *)
    fail "Unknown argument: $1. Usage: $0 [--e2e]"
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
