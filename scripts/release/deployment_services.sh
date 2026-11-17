#!/usr/bin/env bash
#
# FORGE Deployment Service Management
#
# Author:
# -------
# Ranjoy Sen
#
# Purpose:
# --------
# Validates corporate AI connectivity and manages verified candidate processes.
#
# Responsibilities:
# -----------------
# - Check corporate Ollama connectivity and model availability.
# - Verify recorded API and Nginx process ownership.
# - Stop only processes belonging to the recorded candidate.
# - Fail safely when process ownership cannot be established.

check_corporate_ollama() {
  local ai_config="$1" logs_dir="$2" config_values base_url model tags_file
  mkdir -p "$logs_dir"

  config_values="$("$PYTHON" "$ROOT/scripts/release/deployment_config.py" ollama-config "$ai_config")" || fail "Could not read candidate Ollama configuration."

  base_url="${config_values%%$'\t'*}"
  model="${config_values#*$'\t'}"

  [[ -n "$base_url" && -n "$model" ]] || fail "Invalid candidate Ollama configuration."

  tags_file="$logs_dir/ollama-tags.json"

  printf '\nChecking corporate Ollama: %s\n' "$base_url"

  if ! curl --silent --show-error --fail \
    --connect-timeout 5 --max-time 20 \
    "${base_url}/api/tags" -o "$tags_file"; then
    fail "Corporate Ollama is unreachable at $base_url. Connect to the corporate VPN/network and retry. Local fallback is disabled."
  fi

  "$PYTHON" "$ROOT/scripts/release/deployment_config.py" ollama-model "$tags_file" "$model" ||
    fail "Required model '$model' is not available on corporate Ollama at $base_url."
}

cleanup_previous_candidate_services() {
  local active_data run_dir runtime candidate_id api_pid nginx_pid
  local api_command nginx_command listener_pids pid worker_parent worker_command
  local port remaining

  printf '\nChecking for previous FORGE candidate services...\n'

  if [[ ! -f "$ACTIVE_RUN" ]]; then
    for port in 18875 18876; do
      if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        fail "Port $port is occupied but no active-run ownership metadata exists. Nothing was terminated."
      fi
    done
    printf 'No previous FORGE candidate services are running.\n'
    return 0
  fi

  active_data="$("$PYTHON" "$ROOT/scripts/release/process_ownership.py" "$ACTIVE_RUN" "$TEST_RUNS")" \
    || fail "Could not verify previous candidate ownership. No processes were terminated."

  IFS=$'\t' read -r candidate_id run_dir runtime api_pid nginx_pid <<< "$active_data"

  api_command="$(ps -ww -p "$api_pid" -o command= 2>/dev/null || true)"
  nginx_command="$(ps -ww -p "$nginx_pid" -o command= 2>/dev/null || true)"

  if [[ -n "$api_command" ]]; then
    [[ "$api_command" == "$runtime/.venv/bin/python -m uvicorn app.main:app"* ]] \
      && [[ "$api_command" == *"--port 18875"* ]] \
      || fail "API PID $api_pid does not match the recorded candidate runtime. Nothing was terminated."
  fi

  if [[ -n "$nginx_command" ]]; then
    [[ "$nginx_command" == *"nginx: master process"* ]] \
      && [[ "$nginx_command" == *"-p $run_dir/nginx/"* ]] \
      && [[ "$nginx_command" == *"-c $run_dir/nginx/nginx.conf"* ]] \
      || fail "Nginx PID $nginx_pid does not match the recorded candidate runtime. Nothing was terminated."
  fi

  listener_pids="$(lsof -nP -t -iTCP:18875 -sTCP:LISTEN 2>/dev/null | sort -u || true)"
  if [[ -n "$api_command" ]]; then
    [[ "$listener_pids" == "$api_pid" ]] \
      || fail "API port listener does not match recorded candidate PID $api_pid. Nothing was terminated."
  else
    [[ -z "$listener_pids" ]] \
      || fail "API port is occupied but its recorded process is absent. Nothing was terminated."
  fi

  listener_pids="$(lsof -nP -t -iTCP:18876 -sTCP:LISTEN 2>/dev/null | sort -u || true)"
  if [[ -n "$nginx_command" ]]; then
    [[ -n "$listener_pids" ]] \
      || fail "Nginx master exists but no process owns port 18876. Nothing was terminated."

    printf '%s\n' "$listener_pids" | grep -Fxq "$nginx_pid" \
      || fail "Recorded Nginx master PID $nginx_pid is not a port listener. Nothing was terminated."

    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      [[ "$pid" == "$nginx_pid" ]] && continue

      worker_parent="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
      worker_command="$(ps -ww -p "$pid" -o command= 2>/dev/null || true)"

      [[ "$worker_parent" == "$nginx_pid" ]] \
        && [[ "$worker_command" == "nginx: worker process"* ]] \
        || fail "Port 18876 is held by PID $pid, which is not a verified worker of Nginx master $nginx_pid. Nothing was terminated."
    done <<< "$listener_pids"
  else
    [[ -z "$listener_pids" ]] \
      || fail "Nginx port is occupied but its recorded master process is absent. Nothing was terminated."
  fi

  if [[ -z "$api_command" && -z "$nginx_command" ]]; then
    printf 'Recorded candidate processes are already stopped.\n'
    return 0
  fi

  printf 'Verified candidate %s process ownership.\n' "$candidate_id"

  if [[ -n "$nginx_command" ]]; then
    printf 'Stopping recorded Nginx master PID %s...\n' "$nginx_pid"
    kill -TERM "$nginx_pid" 2>/dev/null || true
  fi

  if [[ -n "$api_command" ]]; then
    printf 'Stopping recorded API PID %s...\n' "$api_pid"
    kill -TERM "$api_pid" 2>/dev/null || true
  fi

  for attempt in $(seq 1 20); do
    remaining=0
    for port in 18875 18876; do
      if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        remaining=1
      fi
    done
    [[ "$remaining" -eq 0 ]] && break
    sleep 1
  done

  for port in 18875 18876; do
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      lsof -nP -iTCP:"$port" -sTCP:LISTEN >&2 || true
      fail "Port $port did not close after recorded candidate shutdown."
    fi
  done

  printf 'PASS: Recorded candidate services stopped. Ports 18875 and 18876 are free.\n'
}
