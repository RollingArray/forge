#!/bin/bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
E2E_ROOT="$ROOT/dist/forge-e2e"
API_PORT="${FORGE_E2E_API_PORT:-18875}"
UI_PORT="${FORGE_E2E_UI_PORT:-18876}"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

cd "$ROOT"

echo "===================================================="
echo " FORGE FULL E2E - CLEAN BUILD AND START"
echo "===================================================="

echo ""
echo "========== 1. STOP EXISTING SERVICES =========="
"$ROOT/scripts/stop-full-e2e-deployment.sh"

echo ""
echo "========== 2. VERIFY PORTS =========="
for port in "$API_PORT" "$UI_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is still occupied:"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN
    fail "Cannot rebuild while port $port is in use."
  fi
  echo "PASS: Port $port is free."
done

echo ""
echo "========== 3. ARCHIVE PREVIOUS BUILD =========="
mkdir -p "$E2E_ROOT"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$E2E_ROOT/forge-e2e-previous-$STAMP"
mkdir -p "$ARCHIVE"

for name in \
  forge-e2e-full-suite \
  forge-deployment \
  forge-e2e-deployment.zip \
  e2e-bootstrap.key
do
  if [[ -e "$E2E_ROOT/$name" ]]; then
    mv "$E2E_ROOT/$name" "$ARCHIVE/$name"
    echo "Archived: $name"
  fi
done

if [[ -z "$(find "$ARCHIVE" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  rmdir "$ARCHIVE"
  echo "No previous active build artifacts to archive."
else
  echo "Previous build preserved at: $ARCHIVE"
fi

echo ""
echo "========== 4. BUILD ANGULAR FRONTEND =========="
npm --prefix frontend run build

echo ""
echo "========== 5. BUILD E2E DEPLOYMENT =========="
python3 scripts/build-e2e-deployment.py

echo ""
echo "========== 6. VERIFY REAL AI CONFIGURATION =========="
AI_CONFIG="$E2E_ROOT/forge-deployment/backend/api/config/ai.json"

python3 - "$AI_CONFIG" <<'PYAI'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
config = json.loads(path.read_text(encoding="utf-8"))

print(json.dumps(config, indent=2))

if config.get("provider") != "ollama":
    raise SystemExit("FAIL: Expected Ollama provider.")

if config.get("base_url") != "http://localhost:11434":
    raise SystemExit("FAIL: Unexpected Ollama base URL.")

print("PASS: Real Ollama access is enabled in the packaged deployment.")
PYAI

echo ""
echo "========== 7. START FRESH DEPLOYMENT =========="
exec "$ROOT/scripts/run-full-e2e-deployment.sh"
