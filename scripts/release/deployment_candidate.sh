#!/usr/bin/env bash
#
# FORGE Deployment Candidate Manager
#
# Author:
# -------
# Ranjoy Sen
#
# Purpose:
# --------
# Creates release candidates and manages their isolated runtime lifecycle.
#
# Responsibilities:
# -----------------
# - Prepare candidate and test-run directories.
# - Start and validate isolated candidate services.
# - Record candidate runtime and process metadata.
# - Coordinate preparation-only and automated E2E execution.

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
  candidate_id="$(date -u +%Y%m%dT%H%M%SZ)-$(printf '%s' "$git_commit" | cut -c1-8)-$("$PYTHON" -c 'import secrets; print(secrets.token_hex(3))')"

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

  "$PYTHON" "$ROOT/scripts/release/candidate.py" create-manifest \
    --output "$candidate_dir/manifest.json" \
    --candidate-id "$candidate_id" \
    --sha "$candidate_sha" \
    --archive "$candidate_zip" \
    --git-commit "$git_commit" \
    --pytest-summary "$OUTPUT/backend-pytest-summary.json"

  chmod 0444 "$candidate_zip" "$candidate_dir/manifest.json" "$candidate_dir/SHA256SUMS"

  printf '\nCandidate created: %s\n' "$candidate_id"
  printf 'Verifying immutable candidate archive...\n'
  actual_sha="$(shasum -a 256 "$candidate_zip" | awk '{print $1}')"
  [[ "$actual_sha" == "$candidate_sha" ]] || fail "Candidate checksum changed during creation."

  /usr/bin/unzip -q "$candidate_zip" -d "$run_dir/runtime"
  [[ -f "$runtime/backend/api/app/main.py" ]] || fail "Extracted candidate API is missing."
  [[ -f "$runtime/frontend/index.html" ]] || fail "Extracted candidate frontend is missing."

  printf '\n== Prepare isolated candidate runtime ==\n'

  "$PYTHON" "$ROOT/scripts/release/deployment_config.py" runtime-email \
    "$ROOT/backend/api/config/email.json" \
    "$runtime/backend/api/config"

  chmod 0600 "$runtime/backend/api/config/email.json"
  check_corporate_ollama "$runtime/backend/api/config/ai.json" "$run_dir/logs"

  "$PYTHON" "$ROOT/scripts/release/runtime_secrets.py" "$run_dir/secrets/jwt.secret"

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
      proxy_read_timeout 210s;
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

  "$PYTHON" "$ROOT/scripts/release/candidate.py" write-runtime-metadata \
    --output "$run_dir/runtime-processes.json" \
    --candidate-id "$candidate_id" \
    --run-dir "$run_dir" \
    --runtime "$runtime" \
    --api-pid "$api_pid" \
    --nginx-pid "$nginx_pid"

  "$PYTHON" "$ROOT/scripts/release/candidate.py" write-active-metadata \
    --output "$ACTIVE_RUN" \
    --candidate-id "$candidate_id" \
    --sha "$candidate_sha" \
    --run-dir "$run_dir" \
    --runtime "$runtime" \
    --api-pid "$api_pid" \
    --nginx-pid "$nginx_pid"

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

  if ! osascript - "$ROOT" "$run_dir" "${FORGE_SKIP_OUTLOOK_DRAFT:-0}" <<'APPLESCRIPT'
on run argv
    set repoRoot to item 1 of argv
    set runDir to item 2 of argv
    set skipOutlookDraft to item 3 of argv
    set exitFile to runDir & "/e2e-process.exit"

    set shellCommand to "cd " & quoted form of repoRoot & " && export FORGE_SKIP_OUTLOOK_DRAFT=" & quoted form of skipOutlookDraft & " && if ./scripts/build-deployment.sh --e2e; then /usr/bin/printf '0' > " & quoted form of exitFile & "; echo 'FORGE E2E completed successfully.'; else /usr/bin/printf '1' > " & quoted form of exitFile & "; echo 'FORGE E2E failed. Review the candidate test-run logs.'; fi"

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
