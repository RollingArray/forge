#!/bin/bash

set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend/api"
FRONTEND="$ROOT/frontend"
PYTHON="$ROOT/.venv/bin/python"
NG="$FRONTEND/node_modules/.bin/ng"

BACKEND_PORT=8000
FRONTEND_PORT=4200

LOG_DIR="${TMPDIR:-/tmp}/forge-dev-logs"
mkdir -p "$LOG_DIR"

BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

BACKEND_PID=""
FRONTEND_PID=""
CLEANING_UP=0

cd "$ROOT"

echo ""
echo "========================================"
echo "          FORGE DEVELOPMENT"
echo "========================================"
echo ""

cleanup() {
    if [ "$CLEANING_UP" -eq 1 ]; then
        return
    fi

    CLEANING_UP=1

    echo ""
    echo "Stopping FORGE development servers..."

    if [ -n "$FRONTEND_PID" ]; then
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    fi

    if [ -n "$BACKEND_PID" ]; then
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
    fi

    [ -n "$FRONTEND_PID" ] && wait "$FRONTEND_PID" 2>/dev/null || true
    [ -n "$BACKEND_PID" ] && wait "$BACKEND_PID" 2>/dev/null || true

    echo "FORGE development servers stopped."
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

fail() {
    echo ""
    echo "ERROR: $1"
    exit 1
}

check_command() {
    command -v "$1" >/dev/null 2>&1 || fail "$1 is not installed or not in PATH."
}

check_port() {
    local port="$1"

    if lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
        echo ""
        echo "Port $port is already occupied:"
        lsof -nP -iTCP:"$port" -sTCP:LISTEN
        fail "Please stop the existing process before starting FORGE."
    fi
}

echo "[1/5] Checking development tools..."

check_command uv
check_command node
check_command npm

[ -x "$PYTHON" ] || fail "Root Python environment not found: $PYTHON"
[ -x "$NG" ] || fail "Angular CLI not found. Run npm install inside frontend/."

echo "Python: $("$PYTHON" --version)"
echo "Node: $(node --version)"
echo "npm: $(npm --version)"
echo ""

echo "[2/5] Checking ports..."

check_port "$BACKEND_PORT"
check_port "$FRONTEND_PORT"

echo "Backend port $BACKEND_PORT is available."
echo "Frontend port $FRONTEND_PORT is available."
echo ""

echo "[3/5] Synchronizing Python dependencies..."

uv sync \
    --project "$ROOT" \
    --python "$PYTHON" \
    --locked \
    --no-dev \
    --no-install-project

echo ""
echo "Python environment ready."
echo ""

echo "[4/5] Starting FastAPI backend..."

: > "$BACKEND_LOG"

"$PYTHON" -m uvicorn app.main:app \
    --app-dir "$BACKEND" \
    --host 127.0.0.1 \
    --port "$BACKEND_PORT" \
    --reload \
    > "$BACKEND_LOG" 2>&1 &

BACKEND_PID=$!

echo "Backend process started: $BACKEND_PID"
echo "Backend log: $BACKEND_LOG"
echo ""

echo "[5/5] Starting Angular frontend..."

: > "$FRONTEND_LOG"

(
    cd "$FRONTEND"
    exec "$NG" serve --host 127.0.0.1 --port "$FRONTEND_PORT"
) > "$FRONTEND_LOG" 2>&1 &

FRONTEND_PID=$!

echo "Frontend process started: $FRONTEND_PID"
echo "Frontend log: $FRONTEND_LOG"
echo ""

echo "========================================"
echo "          FORGE STARTING"
echo "========================================"
echo ""
echo "Backend:  http://127.0.0.1:8000"
echo "API Docs: http://127.0.0.1:8000/docs"
echo "Frontend: http://localhost:4200"
echo ""
echo "Logs:"
echo "Backend:  $BACKEND_LOG"
echo "Frontend: $FRONTEND_LOG"
echo ""
echo "Press CTRL+C to stop both servers."
echo ""

# Monitor both processes.
while kill -0 "$BACKEND_PID" 2>/dev/null &&
      kill -0 "$FRONTEND_PID" 2>/dev/null; do
    sleep 2
done

echo ""
echo "WARNING: One of the development servers has stopped."

echo ""
echo "--- BACKEND LOG (last 40 lines) ---"
tail -40 "$BACKEND_LOG" 2>/dev/null || true

echo ""
echo "--- FRONTEND LOG (last 40 lines) ---"
tail -40 "$FRONTEND_LOG" 2>/dev/null || true

exit 1
