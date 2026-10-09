#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE_ROOT="$ROOT/dist/forge-live-test"
APP_ROOT="$LIVE_ROOT/forge-deployment"
NGINX_CONF="$LIVE_ROOT/nginx.conf"
ZIP="$ROOT/dist/forge-deployment.zip"

API_PORT=18765
NGINX_PORT=18766

export FORGE_FRONTEND_BASE_URL="${FORGE_FRONTEND_BASE_URL:-http://127.0.0.1:${NGINX_PORT}}"

echo "===================================================="
echo " FORGE — CLEAN, REBUILD, EXTRACT AND RUN"
echo "===================================================="
echo "Repository: $ROOT"
echo "Frontend URL: $FORGE_FRONTEND_BASE_URL"
echo ""

cd "$ROOT"

for tool in bash python3 curl unzip lsof ps awk grep sort nginx uv; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: Required tool not found: $tool" >&2
        exit 1
    }
done

listener_pids() {
    lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null | sort -u || true
}

wait_for_port_to_clear() {
    local port="$1"
    local attempt

    for attempt in $(seq 1 15); do
        [[ -z "$(listener_pids "$port")" ]] && return 0
        sleep 1
    done

    return 1
}

echo "========== 1. STOP PREVIOUS FORGE TEST DEPLOYMENT =========="

# Stop Nginx only if its master command identifies this exact
# deployment directory.
if [[ -n "$(listener_pids "$NGINX_PORT")" ]]; then
    NGINX_MASTER_PID="$(
        ps -axo pid=,command= |
            grep '[n]ginx: master process' |
            grep -F "$LIVE_ROOT/nginx-prefix/" |
            awk 'NR == 1 {print $1}'
    )"

    if [[ -z "$NGINX_MASTER_PID" ]]; then
        echo "ERROR: Port $NGINX_PORT is occupied by an unrecognized process."
        lsof -nP -iTCP:"$NGINX_PORT" -sTCP:LISTEN || true
        echo "Refusing to stop unrelated processes or delete dist."
        exit 1
    fi

    echo "Found FORGE Nginx master PID $NGINX_MASTER_PID."

    if [[ -f "$NGINX_CONF" ]]; then
        nginx -p "$LIVE_ROOT/nginx-prefix/" \
            -c "$NGINX_CONF" -s quit
    else
        echo "Nginx configuration is missing; sending graceful QUIT to the confirmed master."
        kill -QUIT "$NGINX_MASTER_PID"
    fi

    if ! wait_for_port_to_clear "$NGINX_PORT"; then
        echo "ERROR: Nginx did not release port $NGINX_PORT."
        lsof -nP -iTCP:"$NGINX_PORT" -sTCP:LISTEN || true
        exit 1
    fi

    echo "FORGE Nginx stopped."
else
    echo "No process is listening on port $NGINX_PORT."
fi

# Stop the API only if its process command identifies the extracted
# FORGE virtual environment/application.
if [[ -n "$(listener_pids "$API_PORT")" ]]; then
    for pid in $(listener_pids "$API_PORT"); do
        command_line="$(ps -p "$pid" -o command= 2>/dev/null || true)"

        if [[ "$command_line" != *"$APP_ROOT/"* ]]; then
            echo "ERROR: Port $API_PORT is occupied by an unrecognized process."
            ps -p "$pid" -o pid=,ppid=,command= || true
            echo "Refusing to stop unrelated processes or delete dist."
            exit 1
        fi

        echo "Stopping FORGE API PID $pid..."
        kill -TERM "$pid"
    done

    if ! wait_for_port_to_clear "$API_PORT"; then
        echo "ERROR: API did not release port $API_PORT."
        lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN || true
        exit 1
    fi

    echo "FORGE API stopped."
else
    echo "No process is listening on port $API_PORT."
fi

echo ""
echo "========== 2. VERIFY PORTS ARE FREE =========="

for port in "$API_PORT" "$NGINX_PORT"; do
    if [[ -n "$(listener_pids "$port")" ]]; then
        echo "ERROR: Port $port remains occupied."
        lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
        echo "Refusing to delete dist."
        exit 1
    fi
    echo "Port $port: FREE"
done

echo ""
echo "========== 3. REMOVE PREVIOUS DIST DIRECTORY =========="

if [[ "$ROOT" != "/Users/e10936535/forge" ||
      "$ROOT/dist" != "/Users/e10936535/forge/dist" ]]; then
    echo "ERROR: Unexpected repository path. Refusing to delete dist."
    exit 1
fi

rm -rf -- "$ROOT/dist"
echo "Removed old dist directory and all previous deployment artifacts."

echo ""
echo "========== 4. BUILD DEPLOYMENT =========="

bash "$ROOT/scripts/build-deployment.sh"

echo ""
echo "========== 5. VERIFY DEPLOYMENT ZIP =========="

if [[ ! -s "$ZIP" ]]; then
    echo "ERROR: Deployment ZIP was not created: $ZIP"
    exit 1
fi

unzip -t "$ZIP" | tail -n 2
ls -lh "$ZIP"

echo ""
echo "========== 6. EXTRACT AND START DEPLOYMENT =========="
echo "Open: http://127.0.0.1:${NGINX_PORT}/"
echo ""

exec bash "$ROOT/scripts/run-extracted-deployment.sh"
