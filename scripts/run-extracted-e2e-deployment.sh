#!/bin/bash
set -Eeuo pipefail

ROOT="/Users/e10936535/forge"
E2E_ROOT="$ROOT/dist/forge-e2e"
ZIP="$E2E_ROOT/forge-e2e-deployment.zip"
KEY_FILE="$E2E_ROOT/e2e-bootstrap.key"
LIVE_ROOT="$E2E_ROOT/forge-e2e-live-test"
APP_ROOT="$LIVE_ROOT/forge-deployment"

API_PORT=18865
NGINX_PORT=18866
UV="/opt/homebrew/bin/uv"

API_PID=""
NGINX_STARTED=0

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

cleanup() {
  echo ""
  echo "Stopping isolated E2E services..."

  if [[ "$NGINX_STARTED" == "1" ]]; then
    nginx -p "$LIVE_ROOT/nginx-prefix/" \
      -c "$LIVE_ROOT/nginx.conf" -s stop \
      >/dev/null 2>&1 || true
  fi

  if [[ -n "$API_PID" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" 2>/dev/null || true
  fi

  rm -f "$LIVE_ROOT/api.pid"

  echo "E2E runtime data and logs have been preserved:"
  echo "$LIVE_ROOT"
}
trap cleanup EXIT INT TERM

cd "$ROOT"

[[ -f "$ZIP" ]] || fail "E2E deployment ZIP missing: $ZIP"
[[ -f "$KEY_FILE" ]] || fail "E2E bootstrap key missing: $KEY_FILE"
[[ -x "$UV" ]] || fail "uv executable not found: $UV"
command -v nginx >/dev/null || fail "nginx is not installed."
command -v lsof >/dev/null || fail "lsof is not installed."
command -v curl >/dev/null || fail "curl is not installed."

[[ ! -e "$LIVE_ROOT" ]] || fail \
  "E2E runtime already exists. Refusing to overwrite it: $LIVE_ROOT"

for port in "$API_PORT" "$NGINX_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "Port $port is already in use."
  fi
done

echo "========== 1. EXTRACT ISOLATED E2E PACKAGE =========="

mkdir -p "$LIVE_ROOT"
unzip -q "$ZIP" -d "$LIVE_ROOT"

[[ -f "$APP_ROOT/frontend/index.html" ]] || fail \
  "Extracted Angular index.html is missing."
[[ -f "$APP_ROOT/backend/api/app/main.py" ]] || fail \
  "Extracted backend main.py is missing."
[[ -f "$APP_ROOT/backend/api/app/api/e2e_auth.py" ]] || fail \
  "E2E authentication router is missing."

echo "Extracted E2E application: $APP_ROOT"

echo ""
echo "========== 2. INSTALL LOCKED BACKEND DEPENDENCIES =========="

cd "$APP_ROOT"
"$UV" sync --locked --no-dev --no-group experiments

[[ -x "$APP_ROOT/.venv/bin/python" ]] || fail \
  "Extracted backend Python environment was not created."

echo ""
echo "========== 3. START ISOLATED FASTAPI =========="

export FORGE_E2E_BOOTSTRAP_KEY
FORGE_E2E_BOOTSTRAP_KEY="$(cat "$KEY_FILE")"
[[ -n "$FORGE_E2E_BOOTSTRAP_KEY" ]] || fail \
  "E2E bootstrap key is empty."

(
  cd "$APP_ROOT/backend/api"
  exec "$APP_ROOT/.venv/bin/python" -m uvicorn \
    app.main:app \
    --host 127.0.0.1 \
    --port "$API_PORT"
) > "$LIVE_ROOT/api.log" 2>&1 &

API_PID=$!
printf '%s\n' "$API_PID" > "$LIVE_ROOT/api.pid"

READY=0
for i in $(seq 1 45); do
  if curl --silent --fail \
    "http://127.0.0.1:$API_PORT/health" \
    > "$LIVE_ROOT/health.json"; then
    READY=1
    break
  fi

  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "FAIL: E2E FastAPI stopped during startup."
    cat "$LIVE_ROOT/api.log"
    exit 1
  fi

  sleep 1
done

[[ "$READY" == "1" ]] || {
  echo "FAIL: E2E API health check timed out."
  cat "$LIVE_ROOT/api.log"
  exit 1
}

cat "$LIVE_ROOT/health.json"
echo ""
echo "PASS: Isolated E2E FastAPI is healthy."

echo ""
echo "========== 4. CONFIGURE ISOLATED NGINX =========="

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
        listen 127.0.0.1:$NGINX_PORT;
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

nginx -t -p "$LIVE_ROOT/nginx-prefix/" \
  -c "$LIVE_ROOT/nginx.conf"

nginx -p "$LIVE_ROOT/nginx-prefix/" \
  -c "$LIVE_ROOT/nginx.conf"

NGINX_STARTED=1

echo ""
echo "========== 5. VERIFY E2E DEPLOYMENT =========="

curl --silent --show-error --fail \
  "http://127.0.0.1:$NGINX_PORT/" \
  -o "$LIVE_ROOT/homepage.html"

curl --silent --show-error --fail \
  "http://127.0.0.1:$NGINX_PORT/health"

echo ""
echo ""
echo "===================================================="
echo " ISOLATED FORGE E2E DEPLOYMENT IS RUNNING"
echo "===================================================="
echo "UI:       http://127.0.0.1:$NGINX_PORT/"
echo "API:      http://127.0.0.1:$API_PORT/"
echo "Health:   http://127.0.0.1:$NGINX_PORT/health"
echo ""
echo "Runtime:  $LIVE_ROOT"
echo "API log:  $LIVE_ROOT/api.log"
echo "Nginx:    $LIVE_ROOT/nginx-access.log"
echo ""
echo "Keep this terminal open during testing."
echo "Press Ctrl+C to stop the E2E services."
echo ""

while kill -0 "$API_PID" 2>/dev/null; do
  sleep 2
done

echo "FAIL: E2E FastAPI exited. Inspect $LIVE_ROOT/api.log"
exit 1
