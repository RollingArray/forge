#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"
OUTPUT="$ROOT/dist"
STAGE="$OUTPUT/forge-deployment"
ZIP="$OUTPUT/forge-deployment.zip"
TEST_LOG="$OUTPUT/forge-deployment-smoke-test.log"

fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
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
rm -rf -- "$OUTPUT" "$FRONTEND/dist"
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
import json, secrets, sys
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
email.setdefault("magic_link", {})["frontend_base_url"] = "https://REPLACE-WITH-FORGE-HOST"

token = auth.get("development_token", {})
sanitized_auth = {
    "allowed_domains": auth.get("allowed_domains", []),
    "development_token": {
        "algorithm": token.get("algorithm", "HS256"),
        "expiration_minutes": token.get("expiration_minutes", 60),
        # Fresh per-build secret; replace/rotate on the target host before production use.
        "secret": secrets.token_urlsafe(48),
    },
}
for name, obj in (("ai.json", ai), ("email.json", email), ("authentication.json", sanitized_auth)):
    (dst_cfg / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

# Preserve source email/SMTP settings, but configure the staged magic-link URL.
# FORGE_FRONTEND_BASE_URL is supplied by the rebuild launcher for local testing.
# If unset, leave an explicit placeholder for deployment configuration.
python3 - "$ROOT/backend/api/config/email.json" "$STAGE/backend/api/config/email.json" <<'PY_EMAIL'
import json
import os
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
staged_path = Path(sys.argv[2])

with source_path.open(encoding="utf-8") as f:
    email = json.load(f)

frontend_base_url = os.environ.get(
    "FORGE_FRONTEND_BASE_URL",
    "https://REPLACE-WITH-FORGE-HOST",
).strip().rstrip("/")

if not frontend_base_url.startswith(("http://", "https://")):
    raise SystemExit("ERROR: FORGE_FRONTEND_BASE_URL must be an HTTP(S) URL.")

email.setdefault("magic_link", {})["frontend_base_url"] = frontend_base_url

with staged_path.open("w", encoding="utf-8") as f:
    json.dump(email, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"Staged email configuration with frontend URL: {frontend_base_url}")
PY_EMAIL

cat > "$STAGE/README-DEPLOYMENT.md" <<'README'
# FORGE Deployment Bundle

This bundle contains the compiled Angular frontend, FastAPI application source,
the repository's locked Python dependency definitions and deployment configuration.
It does not contain `.git`, `node_modules`, virtual environments, local runtime JSON
data, or your development authentication secret.

## Contents
- `frontend/` — compiled Angular browser application; Node.js is not needed to serve it.
- `backend/api/app/` — FastAPI application, templates and assets.
- `backend/api/config/` — application configuration. `email.json` is copied unchanged from the source repository; verify it is approved for distribution.
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
- Replace/rotate `development_token.secret` on the target host and confirm `allowed_domains` with the application owner.
- If SMTP authentication is required, provide `FORGE_SMTP_PASSWORD` through the approved secret/environment mechanism. Do not put SMTP passwords in JSON or ZIP files.
- Ensure the host can reach the corporate profile API over HTTPS and trusts the corporate certificate chain.

The included authentication secret is freshly generated for this release, not copied from the developer machine. Rotate it on the target host before production use. The packaged `email.json` is copied unchanged from the source repository. Confirm its SMTP settings and frontend URL are correct for the target environment.

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

printf '\nDeployment bundle created:\n  %s\n' "$ZIP"
printf 'Bundle size: %s\n' "$(du -h "$ZIP" | awk '{print $1}')"
printf 'Smoke-test log: %s\n' "$TEST_LOG"
printf '\nReview README-DEPLOYMENT.md and config files in dist/forge-deployment before transferring.\n'
