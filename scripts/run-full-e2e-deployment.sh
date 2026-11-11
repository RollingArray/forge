#!/bin/bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
E2E_ROOT="$ROOT/dist/forge-e2e"

RUNTIME_ARG="${FORGE_E2E_RUNTIME_DIR:-$E2E_ROOT/forge-e2e-full-suite}"
API_PORT="${FORGE_E2E_API_PORT:-18875}"
UI_PORT="${FORGE_E2E_UI_PORT:-18876}"
export FORGE_FRONTEND_BASE_URL="${FORGE_FRONTEND_BASE_URL:-http://127.0.0.1:${UI_PORT}}"
UV="${UV_BIN:-$(command -v uv || true)}"

if [[ "$RUNTIME_ARG" = /* ]]; then
  LIVE_ROOT="$RUNTIME_ARG"
else
  LIVE_ROOT="$ROOT/$RUNTIME_ARG"
fi

ZIP="$E2E_ROOT/forge-e2e-deployment.zip"
KEY_FILE="${FORGE_E2E_BOOTSTRAP_KEY_FILE:-$E2E_ROOT/e2e-bootstrap.key}"
APP_ROOT="$LIVE_ROOT/forge-deployment"

API_PID=""
NGINX_STARTED=0

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

cleanup() {
  echo ""
  echo "Stopping full-suite E2E services..."

  if [[ "$NGINX_STARTED" == "1" ]]; then
    nginx -p "$LIVE_ROOT/nginx-prefix/" \
      -c "$LIVE_ROOT/nginx.conf" -s stop >/dev/null 2>&1 || true
  fi

  if [[ -n "$API_PID" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" 2>/dev/null || true
  fi

  echo "Runtime data and logs preserved:"
  echo "$LIVE_ROOT"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

[[ "$LIVE_ROOT" == "$E2E_ROOT/"* ]] || fail \
  "Runtime directory must be inside $E2E_ROOT"
[[ "$LIVE_ROOT" != "$E2E_ROOT" ]] || fail "Runtime directory cannot be the package root."
[[ -f "$ZIP" ]] || fail "E2E deployment ZIP missing: $ZIP"
[[ -f "$KEY_FILE" ]] || fail "E2E bootstrap key missing: $KEY_FILE"
[[ -x "$UV" ]] || fail "uv executable not found: $UV"
command -v nginx >/dev/null || fail "nginx is not installed."
command -v lsof >/dev/null || fail "lsof is not installed."
command -v curl >/dev/null || fail "curl is not installed."
command -v unzip >/dev/null || fail "unzip is not installed."

[[ "$API_PORT" =~ ^[0-9]+$ ]] || fail "API port must be numeric."
[[ "$UI_PORT" =~ ^[0-9]+$ ]] || fail "UI port must be numeric."
[[ "$API_PORT" != "$UI_PORT" ]] || fail "API and UI ports must differ."
[[ ! -e "$LIVE_ROOT" ]] || fail \
  "Runtime already exists. Refusing to overwrite: $LIVE_ROOT"

for port in "$API_PORT" "$UI_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "Port $port is already in use."
  fi
done

echo "========== 1. EXTRACT E2E PACKAGE =========="
mkdir -p "$LIVE_ROOT"
unzip -q "$ZIP" -d "$LIVE_ROOT"

EMAIL_CONFIG_PATH="$APP_ROOT/backend/api/config/email.json" \
FRONTEND_BASE_URL="http://127.0.0.1:${UI_PORT}" \
python3 - <<'PYCONFIG'
import json
import os
from pathlib import Path

path = Path(os.environ["EMAIL_CONFIG_PATH"])
config = json.loads(path.read_text(encoding="utf-8"))
config.setdefault("magic_link", {})["frontend_base_url"] = os.environ["FRONTEND_BASE_URL"]
path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
print("Configured isolated magic-link URL:", os.environ["FRONTEND_BASE_URL"])
PYCONFIG

[[ -f "$APP_ROOT/frontend/index.html" ]] || fail "Extracted frontend index.html is missing."
[[ -f "$APP_ROOT/backend/api/app/main.py" ]] || fail "Extracted backend main.py is missing."
[[ -f "$APP_ROOT/backend/api/app/api/e2e_auth.py" ]] || fail "E2E authentication router is missing."

echo "PASS: Package extracted to $LIVE_ROOT"

echo ""
echo "========== 2. INSTALL LOCKED BACKEND DEPENDENCIES =========="
cd "$APP_ROOT"
"$UV" sync --locked --no-dev --no-group experiments
[[ -x "$APP_ROOT/.venv/bin/python" ]] || fail "Backend Python environment was not created."

echo ""
echo "========== 3. START FASTAPI =========="
export FORGE_E2E_BOOTSTRAP_KEY
FORGE_E2E_BOOTSTRAP_KEY="$(cat "$KEY_FILE")"
[[ -n "$FORGE_E2E_BOOTSTRAP_KEY" ]] || fail "E2E bootstrap key is empty."

(
  cd "$APP_ROOT/backend/api"
  exec "$APP_ROOT/.venv/bin/python" -m uvicorn \
    app.main:app --host 127.0.0.1 --port "$API_PORT"
) > "$LIVE_ROOT/api.log" 2>&1 &

API_PID=$!
printf '%s\n' "$API_PID" > "$LIVE_ROOT/api.pid"

READY=0
for i in $(seq 1 45); do
  if curl --silent --fail "http://127.0.0.1:$API_PORT/health" \
    > "$LIVE_ROOT/health.json"; then
    READY=1
    break
  fi

  if ! kill -0 "$API_PID" 2>/dev/null; then
    cat "$LIVE_ROOT/api.log"
    fail "FastAPI exited during startup."
  fi
  sleep 1
done

[[ "$READY" == "1" ]] || {
  cat "$LIVE_ROOT/api.log"
  fail "API health check timed out."
}

echo "PASS: FastAPI is healthy."

echo ""
echo "========== 4. CONFIGURE NGINX =========="
mkdir -p "$LIVE_ROOT/nginx-prefix/logs"

cat > "$LIVE_ROOT/nginx.conf" <<EOF
worker_processes 1;
pid $LIVE_ROOT/nginx.pid;
error_log $LIVE_ROOT/nginx-error.log;

events {
    worker_connections 128;
}

http {
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
    access_log $LIVE_ROOT/nginx-access.log;

    server {
        listen 127.0.0.1:$UI_PORT;
        server_name localhost;
        root $APP_ROOT/frontend;
        index index.html;

        location /api/ {
            proxy_pass http://127.0.0.1:$API_PORT;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location = /health {
            proxy_pass http://127.0.0.1:$API_PORT/health;
        }

        location / {
            try_files \$uri \$uri/ /index.html;
        }
    }
}
EOF

nginx -t -p "$LIVE_ROOT/nginx-prefix/" -c "$LIVE_ROOT/nginx.conf"
nginx -p "$LIVE_ROOT/nginx-prefix/" -c "$LIVE_ROOT/nginx.conf"
NGINX_STARTED=1

echo ""
echo "========== 5. VERIFY DEPLOYMENT =========="
curl --silent --show-error --fail \
  "http://127.0.0.1:$UI_PORT/" -o "$LIVE_ROOT/homepage.html"
curl --silent --show-error --fail \
  "http://127.0.0.1:$UI_PORT/health"

echo ""
echo "===================================================="
echo " FULL-SUITE FORGE E2E DEPLOYMENT IS RUNNING"
echo "===================================================="
echo "UI:       http://127.0.0.1:$UI_PORT/"
echo "API:      http://127.0.0.1:$API_PORT/"
echo "Runtime:  $LIVE_ROOT"
echo "Key:      $KEY_FILE"
echo ""
echo "Keep this terminal open during testing."
echo "Press Ctrl+C to stop the services."
echo ""
echo "NEXT: Open a NEW terminal and run:"
echo "  cd $ROOT/frontend"
echo "  npm run test:e2e:full"
echo ""

while kill -0 "$API_PID" 2>/dev/null; do
  sleep 2
done

fail "FastAPI exited. Inspect $LIVE_ROOT/api.log"
