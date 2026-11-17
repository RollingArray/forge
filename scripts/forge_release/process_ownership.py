#!/usr/bin/env python3
"""Verify ownership of isolated FORGE candidate services."""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.forge_release.validation import (
    ValidationError,
    validate_candidate_artifacts,
)


def command_for(pid):
    result = subprocess.run(
        ["ps", "-ww", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def parent_for(pid):
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "ppid="],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def listeners(port):
    result = subprocess.run(
        ["lsof", "-nP", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    return sorted({
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    })


def resolve_candidate_processes(active_path, test_runs_path):
    active_path = Path(active_path)
    test_runs = Path(test_runs_path).resolve()

    try:
        active = json.loads(active_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read active-run metadata: {exc}") from exc

    candidate_id = str(active.get("candidate_id", ""))
    run_dir_value = str(active.get("run_dir", ""))
    active_sha = str(active.get("sha256", ""))

    if not candidate_id or not run_dir_value or not active_sha:
        raise ValueError("Active run does not identify a candidate, checksum and run directory.")

    run_dir = Path(run_dir_value).resolve()

    if not run_dir.is_relative_to(test_runs) or run_dir == test_runs:
        raise ValueError("Active run directory is outside the FORGE test-runs directory.")

    candidate_dir = test_runs.parent / "candidates" / candidate_id

    try:
        validate_candidate_artifacts(
            candidate_dir,
            candidate_id,
            expected_sha=active_sha,
        )
    except (ValidationError, OSError, ValueError) as exc:
        raise ValueError(f"Candidate artifact verification failed: {exc}") from exc

    runtime = (run_dir / "runtime" / "forge-deployment").resolve()
    metadata_path = run_dir / "runtime-processes.json"

    if not metadata_path.is_file():
        return discover_legacy_processes(
            candidate_id,
            run_dir,
            runtime,
        )

    try:
        metadata = json.loads(metadata_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read runtime process metadata: {exc}") from exc

    if metadata.get("candidate_id") != candidate_id:
        raise ValueError("Runtime process candidate ID does not match active run.")

    if Path(str(metadata.get("run_dir", ""))).resolve() != run_dir:
        raise ValueError("Runtime process run directory does not match active run.")

    if Path(str(metadata.get("runtime", ""))).resolve() != runtime:
        raise ValueError("Runtime process path does not match the expected candidate runtime.")

    api_pid = metadata.get("api_pid")
    nginx_pid = metadata.get("nginx_pid")

    if (
        not isinstance(api_pid, int)
        or isinstance(api_pid, bool)
        or not isinstance(nginx_pid, int)
        or isinstance(nginx_pid, bool)
        or api_pid <= 1
        or nginx_pid <= 1
        or api_pid == nginx_pid
    ):
        raise ValueError("Runtime process PIDs are invalid.")

    if metadata.get("api_port") != 18875 or metadata.get("nginx_port") != 18876:
        raise ValueError("Runtime process ports do not match the FORGE candidate ports.")

    return candidate_id, run_dir, runtime, api_pid, nginx_pid


def discover_legacy_processes(candidate_id, run_dir, runtime):
    api_listeners = listeners(18875)
    nginx_listeners = listeners(18876)

    if len(api_listeners) != 1:
        raise ValueError("Legacy candidate API listener is missing or ambiguous.")

    api_pid = int(api_listeners[0])
    api_command = command_for(api_pid)
    expected_api = (
        str(runtime / ".venv" / "bin" / "python")
        + " -m uvicorn app.main:app"
    )

    if not api_command.startswith(expected_api) or "--port 18875" not in api_command:
        raise ValueError(
            "Port 18875 is not owned by the expected legacy candidate API."
        )

    nginx_masters = []

    for pid_text in nginx_listeners:
        command = command_for(pid_text)
        if (
            "nginx: master process" in command
            and f"-p {run_dir}/nginx/" in command
            and f"-c {run_dir}/nginx/nginx.conf" in command
        ):
            nginx_masters.append(pid_text)

    if len(nginx_masters) != 1:
        raise ValueError("Legacy candidate Nginx master is missing or ambiguous.")

    nginx_pid = int(nginx_masters[0])

    for pid_text in nginx_listeners:
        pid = int(pid_text)
        if pid == nginx_pid:
            continue

        if (
            parent_for(pid) != str(nginx_pid)
            or not command_for(pid).startswith("nginx: worker process")
        ):
            raise ValueError(
                f"Port 18876 has an unverified listener (PID {pid}). "
                "Nothing was terminated."
            )

    return candidate_id, run_dir, runtime, api_pid, nginx_pid


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: process_ownership.py ACTIVE_RUN TEST_RUNS"
        )

    try:
        result = resolve_candidate_processes(sys.argv[1], sys.argv[2])
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from exc

    candidate_id, run_dir, runtime, api_pid, nginx_pid = result

    print("\t".join((
        candidate_id,
        str(run_dir),
        str(runtime),
        str(api_pid),
        str(nginx_pid),
    )))


if __name__ == "__main__":
    main()
