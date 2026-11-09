#!/bin/bash
set -Eeuo pipefail

ROOT="/Users/e10936535/forge"
LIVE_ROOT="$ROOT/dist/forge-e2e/forge-e2e-live-test"
API_PID_FILE="$LIVE_ROOT/api.pid"
NGINX_CONF="$LIVE_ROOT/nginx.conf"
NGINX_PREFIX="$LIVE_ROOT/nginx-prefix"

API_STOPPED=0
NGINX_STOPPED=0

echo "========== STOP ISOLATED FORGE E2E =========="

if [[ ! -d "$LIVE_ROOT" ]]; then
  echo "No extracted E2E runtime exists."
  exit 0
fi

if [[ -f "$API_PID_FILE" ]]; then
  API_PID="$(cat "$API_PID_FILE")"

  if [[ "$API_PID" =~ ^[0-9]+$ ]] && kill -0 "$API_PID" 2>/dev/null; then
    PROCESS_COMMAND="$(ps -p "$API_PID" -o command= 2>/dev/null || true)"

    EXPECTED_PYTHON="$LIVE_ROOT/forge-deployment/.venv/bin/python"

    if [[ "$PROCESS_COMMAND" == *"$EXPECTED_PYTHON"* ]] &&
       [[ "$PROCESS_COMMAND" == *"uvicorn"* ]] &&
       [[ "$PROCESS_COMMAND" == *"app.main:app"* ]] &&
       [[ "$PROCESS_COMMAND" == *"--port 18865"* ]]; then
      echo "Stopping verified E2E API process: $API_PID"
      kill "$API_PID"

      for i in $(seq 1 15); do
        if ! kill -0 "$API_PID" 2>/dev/null; then
          API_STOPPED=1
          break
        fi
        sleep 1
      done

      if [[ "$API_STOPPED" != "1" ]]; then
        echo "FAIL: E2E API did not stop within 15 seconds."
        exit 1
      fi
    else
      echo "WARNING: PID $API_PID does not match the expected E2E API command."
      echo "Process was not signalled."
      echo "$PROCESS_COMMAND"
      exit 1
    fi
  else
    echo "E2E API PID is not running."
    API_STOPPED=1
  fi
else
  echo "No E2E API PID file found."
  API_STOPPED=1
fi

if [[ -f "$NGINX_CONF" ]] && [[ -d "$NGINX_PREFIX" ]]; then
  NGINX_PID_FILE="$LIVE_ROOT/nginx.pid"

  if [[ -f "$NGINX_PID_FILE" ]]; then
    NGINX_PID="$(cat "$NGINX_PID_FILE")"

    if [[ "$NGINX_PID" =~ ^[0-9]+$ ]] &&
       kill -0 "$NGINX_PID" 2>/dev/null; then
      NGINX_COMMAND="$(ps -p "$NGINX_PID" -o command= 2>/dev/null || true)"

      if [[ "$NGINX_COMMAND" == *"$NGINX_PREFIX"* ]] &&
         [[ "$NGINX_COMMAND" == *"$NGINX_CONF"* ]]; then
        echo "Stopping verified E2E Nginx process: $NGINX_PID"
        nginx -p "$NGINX_PREFIX/" -c "$NGINX_CONF" -s stop

        for i in $(seq 1 15); do
          if ! kill -0 "$NGINX_PID" 2>/dev/null; then
            NGINX_STOPPED=1
            break
          fi
          sleep 1
        done

        if [[ "$NGINX_STOPPED" != "1" ]]; then
          echo "FAIL: E2E Nginx did not stop within 15 seconds."
          exit 1
        fi
      else
        echo "WARNING: Nginx PID does not match the E2E configuration."
        echo "Process was not signalled."
        echo "$NGINX_COMMAND"
        exit 1
      fi
    else
      echo "E2E Nginx is not running."
      NGINX_STOPPED=1
    fi
  else
    echo "No E2E Nginx PID file found."
    NGINX_STOPPED=1
  fi
else
  NGINX_STOPPED=1
fi

if [[ "$API_STOPPED" == "1" ]] && [[ "$NGINX_STOPPED" == "1" ]]; then
  rm -f "$API_PID_FILE"
  echo ""
  echo "PASS: E2E services stopped."
  echo "Preserved runtime data, configuration and logs:"
  echo "$LIVE_ROOT"
fi
