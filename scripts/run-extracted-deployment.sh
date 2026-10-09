#!/bin/bash
set -Eeuo pipefail

ROOT="/Users/e10936535/forge"
ZIP="$ROOT/dist/forge-deployment.zip"
LIVE_ROOT="$ROOT/dist/forge-live-test"
APP_ROOT="$LIVE_ROOT/forge-deployment"
API_PORT=18765
NGINX_PORT=18766

# Allow an explicit deployment URL; otherwise use the local Nginx URL.
export FORGE_FRONTEND_BASE_URL="${FORGE_FRONTEND_BASE_URL:-http://127.0.0.1:${NGINX_PORT}}"

API_PID=""
NGINX_STARTED=0

cleanup() {
  echo ""
  echo "Stopping extracted deployment..."

  if [[ "$NGINX_STARTED" == "1" ]]; then
    nginx -p "$LIVE_ROOT/nginx-prefix/" \
      -c "$LIVE_ROOT/nginx.conf" -s stop \
      >/dev/null 2>&1 || true
  fi

  if [[ -n "$API_PID" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" 2>/dev/null || true
  fi

  echo "Stopped. Extracted files and logs remain in:"
  echo "$LIVE_ROOT"
}
trap cleanup EXIT INT TERM

cd "$ROOT"

test -f "$ZIP" || {
  echo "FAIL: Deployment ZIP not found: $ZIP"
  exit 1
}

for port in "$API_PORT" "$NGINX_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "FAIL: Port $port is already in use."
    echo "Stop the other test server or choose different ports."
    exit 1
  fi
done

echo "========== 1. EXTRACT DEPLOYMENT =========="

rm -rf "$LIVE_ROOT"
mkdir -p "$LIVE_ROOT"
unzip -q "$ZIP" -d "$LIVE_ROOT"

test -f "$APP_ROOT/frontend/index.html"
test -f "$APP_ROOT/backend/api/app/main.py"

echo "Extracted application: $APP_ROOT"

echo ""
echo "========== 2. INSTALL BACKEND DEPENDENCIES =========="

cd "$APP_ROOT"
uv sync --locked --no-dev --no-group experiments

echo ""
echo "========== 3. START FASTAPI =========="

(
  cd "$APP_ROOT/backend/api"
  exec "$APP_ROOT/.venv/bin/python" -m uvicorn \
    app.main:app \
    --host 127.0.0.1 \
    --port "$API_PORT"
) > "$LIVE_ROOT/api.log" 2>&1 &

API_PID=$!

READY=0
for i in $(seq 1 30); do
  if curl --silent --fail \
    "http://127.0.0.1:$API_PORT/health" \
    > "$LIVE_ROOT/health.json"; then
    READY=1
    break
  fi

  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "FAIL: FastAPI stopped during startup."
    cat "$LIVE_ROOT/api.log"
    exit 1
  fi

  sleep 1
done

if [[ "$READY" != "1" ]]; then
  echo "FAIL: FastAPI health check timed out."
  cat "$LIVE_ROOT/api.log"
  exit 1
fi

cat "$LIVE_ROOT/health.json"
echo ""
echo "PASS: Backend is running from the extracted package."

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
echo "========== 5. VERIFY THE LIVE DEPLOYMENT =========="

curl --silent --show-error --fail \
  "http://127.0.0.1:$NGINX_PORT/" \
  -o "$LIVE_ROOT/homepage.html"

curl --silent --show-error --fail \
  "http://127.0.0.1:$NGINX_PORT/health"

echo ""
echo ""
echo "PASS: Nginx serves the extracted Angular build."
echo "PASS: Nginx proxies health checks to the extracted FastAPI backend."

echo ""
echo "===================================================="
echo " FORGE EXTRACTED DEPLOYMENT IS RUNNING"
echo "===================================================="
echo "Open this URL in your browser:"
echo ""
echo "  http://127.0.0.1:$NGINX_PORT/"
echo ""
echo "API health:"
echo "  http://127.0.0.1:$NGINX_PORT/health"
echo ""
echo "Extracted application:"
echo "  $APP_ROOT"
echo ""
echo "API log:    $LIVE_ROOT/api.log"
echo "Nginx log:  $LIVE_ROOT/nginx-access.log"
echo ""
echo "Keep this terminal open while testing."
echo "Press Ctrl+C here when finished."
echo ""

# Keep this launcher alive while the API and Nginx serve the UI.
while kill -0 "$API_PID" 2>/dev/null; do
  sleep 2
done

echo "FAIL: FastAPI exited. Inspect $LIVE_ROOT/api.log"
exit 1
