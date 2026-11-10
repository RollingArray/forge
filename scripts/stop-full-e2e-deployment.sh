#!/bin/bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
E2E_ROOT="$ROOT/dist/forge-e2e"
RUNTIME_ARG="${FORGE_E2E_RUNTIME_DIR:-$E2E_ROOT/forge-e2e-full-suite}"
API_PORT="${FORGE_E2E_API_PORT:-18875}"

if [[ "$RUNTIME_ARG" = /* ]]; then
  LIVE_ROOT="$RUNTIME_ARG"
else
  LIVE_ROOT="$ROOT/$RUNTIME_ARG"
fi

[[ "$LIVE_ROOT" == "$E2E_ROOT/"* ]] || {
  echo "FAIL: Runtime must be inside $E2E_ROOT" >&2
  exit 1
}

API_STOPPED=0
NGINX_STOPPED=0

echo "========== STOP FULL-SUITE FORGE E2E =========="

if [[ ! -d "$LIVE_ROOT" ]]; then
  echo "No full-suite runtime exists: $LIVE_ROOT"
  exit 0
fi

API_PID_FILE="$LIVE_ROOT/api.pid"
NGINX_PID_FILE="$LIVE_ROOT/nginx.pid"
NGINX_CONF="$LIVE_ROOT/nginx.conf"
NGINX_PREFIX="$LIVE_ROOT/nginx-prefix"

if [[ -f "$API_PID_FILE" ]]; then
  API_PID="$(cat "$API_PID_FILE")"

  if [[ "$API_PID" =~ ^[0-9]+$ ]] && kill -0 "$API_PID" 2>/dev/null; then
    PROCESS_COMMAND="$(ps -p "$API_PID" -o command= 2>/dev/null || true)"
    EXPECTED_PYTHON="$LIVE_ROOT/forge-deployment/.venv/bin/python"

    if [[ "$PROCESS_COMMAND" == *"$EXPECTED_PYTHON"* ]] &&
       [[ "$PROCESS_COMMAND" == *"uvicorn"* ]] &&
       [[ "$PROCESS_COMMAND" == *"app.main:app"* ]] &&
       [[ "$PROCESS_COMMAND" == *"--port $API_PORT"* ]]; then
      echo "Stopping verified API process: $API_PID"
      kill "$API_PID"

      for i in $(seq 1 15); do
        if ! kill -0 "$API_PID" 2>/dev/null; then
          API_STOPPED=1
          break
        fi
        sleep 1
      done

      [[ "$API_STOPPED" == "1" ]] || {
        echo "FAIL: API did not stop within 15 seconds."
        exit 1
      }
    else
      echo "FAIL: API PID does not match this runtime. Not signalling it."
      echo "$PROCESS_COMMAND"
      exit 1
    fi
  else
    echo "API is not running."
    API_STOPPED=1
  fi
else
  echo "No API PID file found."
  API_STOPPED=1
fi

if [[ -f "$NGINX_PID_FILE" ]] && [[ -f "$NGINX_CONF" ]] && [[ -d "$NGINX_PREFIX" ]]; then
  NGINX_PID="$(cat "$NGINX_PID_FILE")"

  if [[ "$NGINX_PID" =~ ^[0-9]+$ ]] && kill -0 "$NGINX_PID" 2>/dev/null; then
    NGINX_COMMAND="$(ps -p "$NGINX_PID" -o command= 2>/dev/null || true)"

    if [[ "$NGINX_COMMAND" == *"$NGINX_PREFIX"* ]] &&
       [[ "$NGINX_COMMAND" == *"$NGINX_CONF"* ]]; then
      echo "Stopping verified Nginx process: $NGINX_PID"
      nginx -p "$NGINX_PREFIX/" -c "$NGINX_CONF" -s stop

      for i in $(seq 1 15); do
        if ! kill -0 "$NGINX_PID" 2>/dev/null; then
          NGINX_STOPPED=1
          break
        fi
        sleep 1
      done

      [[ "$NGINX_STOPPED" == "1" ]] || {
        echo "FAIL: Nginx did not stop within 15 seconds."
        exit 1
      }
    else
      echo "FAIL: Nginx PID does not match this runtime. Not signalling it."
      echo "$NGINX_COMMAND"
      exit 1
    fi
  else
    echo "Nginx is not running."
    NGINX_STOPPED=1
  fi
else
  echo "Nginx PID/config/prefix not found."
  NGINX_STOPPED=1
fi

if [[ "$API_STOPPED" == "1" && "$NGINX_STOPPED" == "1" ]]; then
  rm -f "$API_PID_FILE"
  echo ""
  echo "PASS: Full-suite E2E services stopped."
  echo "Preserved runtime data, configuration and logs:"
  echo "$LIVE_ROOT"
fi
