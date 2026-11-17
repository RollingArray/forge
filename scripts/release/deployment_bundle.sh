#!/usr/bin/env bash
#
# FORGE Deployment Bundle Builder
#
# Author:
# -------
# Ranjoy Sen
#
# Purpose:
# --------
# Builds, stages, smoke-tests, and packages the FORGE deployment bundle.
#
# Responsibilities:
# -----------------
# - Build the Angular production frontend.
# - Stage sanitized backend and frontend deployment files.
# - Install locked dependencies and run local smoke tests.
# - Verify and package the deployment archive.


build_deployment() {
  local BROWSER DEPLOY_AI_BASE_URL DEPLOY_AI_MODEL UNEXPECTED_DATA
command -v npm >/dev/null 2>&1 || fail "npm is required to build the Angular production frontend."
command -v uv >/dev/null 2>&1 || fail "uv is required to install locked Python dependencies and smoke-test the staged backend."
[[ -x "$PYTHON" ]] || fail "Project Python is required."
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

"$PYTHON" "$ROOT/scripts/release/deployment_config.py" stage-config \
  "$ROOT" "$STAGE" "$DEPLOY_AI_BASE_URL" "$DEPLOY_AI_MODEL"

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
### Configure the JWT signing secret on Windows

Run once in Windows PowerShell as Administrator on the target server:

```powershell
$bytes = New-Object byte[] 48
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$secret = [Convert]::ToBase64String($bytes)
$rng.Dispose()

[Environment]::SetEnvironmentVariable("FORGE_JWT_SECRET", $secret, "Machine")
$env:FORGE_JWT_SECRET = $secret

$stored = [Environment]::GetEnvironmentVariable("FORGE_JWT_SECRET", "Machine")
if ($null -eq $stored -or [System.Text.Encoding]::UTF8.GetByteCount($stored) -lt 32) {
    throw "JWT secret configuration failed."
}

Write-Host "FORGE JWT secret configured successfully."
Remove-Variable secret, stored, bytes
```

Important:
- Run once per deployment environment.
- Preserve the same secret across upgrades. Do not regenerate during routine restarts.
- Restart the API after configuration so the API process inherits the variable.
- Never store the secret in JSON, the deployment ZIP, or logs.
- Confirm `allowed_domains` with the application owner.
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
        proxy_read_timeout 210s;
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
  export FORGE_JWT_SECRET="$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(48))')"
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
      proxy_read_timeout 210s;
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

"$PYTHON" "$ROOT/scripts/release/packaging.py" "$ZIP"

printf '\n== Candidate creation and isolated E2E runtime ==\n'
printf 'Verified deployment ZIP: %s\n' "$ZIP"
printf 'Bundle size: %s\n' "$(du -h "$ZIP" | awk '{print $1}')"
printf 'Smoke-test log: %s\n' "$TEST_LOG"

create_candidate_and_start
}
