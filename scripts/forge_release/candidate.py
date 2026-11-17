"""Candidate manifest and runtime metadata operations for FORGE."""

import argparse
import json
import os
import sys

from datetime import datetime, timezone
from pathlib import Path


def create_manifest(
    manifest_path,
    candidate_id,
    sha,
    archive_path,
    git_commit,
    pytest_summary_path,
):
    manifest_path = Path(manifest_path)
    archive_path = Path(archive_path)
    pytest = json.loads(Path(pytest_summary_path).read_text())

    if pytest.get("status") != "PASSED":
        raise ValueError(
            "Cannot create candidate: backend Pytest did not pass."
        )

    discovered = pytest.get("discovered")
    if isinstance(discovered, bool) or not isinstance(discovered, int) or discovered < 1:
        raise ValueError("Invalid backend Pytest discovery count.")

    if pytest.get("passed") != discovered:
        raise ValueError(
            "Backend Pytest passed count does not match discovery."
        )

    for key in ("failed", "errors", "skipped", "flaky", "unexecuted"):
        if pytest.get(key) != 0:
            raise ValueError(f"Backend Pytest {key} count is nonzero.")

    if not archive_path.is_file():
        raise ValueError("Candidate archive does not exist.")

    data = {
        "candidate_id": candidate_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "archive": archive_path.name,
        "sha256": sha,
        "size_bytes": archive_path.stat().st_size,
        "backend_pytest": pytest,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2) + "\n")
    return data


def write_runtime_metadata(
    metadata_path,
    candidate_id,
    run_dir,
    runtime,
    api_pid,
    nginx_pid,
):
    run_dir = Path(run_dir).resolve()
    runtime = Path(runtime).resolve()

    data = {
        "candidate_id": candidate_id,
        "run_dir": str(run_dir),
        "runtime": str(runtime),
        "api_pid": int(api_pid),
        "nginx_pid": int(nginx_pid),
        "api_port": 18875,
        "nginx_port": 18876,
    }

    path = Path(metadata_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(path)

    return data


def write_active_metadata(
    active_path,
    candidate_id,
    sha,
    run_dir,
    runtime,
    api_pid,
    nginx_pid,
):
    data = {
        "candidate_id": candidate_id,
        "sha256": sha,
        "status": "PREPARED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "runtime": str(runtime),
        "api_pid": int(api_pid),
        "nginx_pid": int(nginx_pid),
        "api_url": "http://127.0.0.1:18875",
        "ui_url": "http://127.0.0.1:18876",
    }

    path = Path(active_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)

    return data


def main():
    parser = argparse.ArgumentParser(
        description="FORGE candidate metadata operations."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    manifest = commands.add_parser("create-manifest")
    manifest.add_argument("--output", required=True)
    manifest.add_argument("--candidate-id", required=True)
    manifest.add_argument("--sha", required=True)
    manifest.add_argument("--archive", required=True)
    manifest.add_argument("--git-commit", required=True)
    manifest.add_argument("--pytest-summary", required=True)

    runtime = commands.add_parser("write-runtime-metadata")
    runtime.add_argument("--output", required=True)
    runtime.add_argument("--candidate-id", required=True)
    runtime.add_argument("--run-dir", required=True)
    runtime.add_argument("--runtime", required=True)
    runtime.add_argument("--api-pid", required=True, type=int)
    runtime.add_argument("--nginx-pid", required=True, type=int)

    active = commands.add_parser("write-active-metadata")
    active.add_argument("--output", required=True)
    active.add_argument("--candidate-id", required=True)
    active.add_argument("--sha", required=True)
    active.add_argument("--run-dir", required=True)
    active.add_argument("--runtime", required=True)
    active.add_argument("--api-pid", required=True, type=int)
    active.add_argument("--nginx-pid", required=True, type=int)

    args = parser.parse_args()

    try:
        if args.command == "create-manifest":
            create_manifest(
                args.output,
                args.candidate_id,
                args.sha,
                args.archive,
                args.git_commit,
                args.pytest_summary,
            )
        elif args.command == "write-runtime-metadata":
            write_runtime_metadata(
                args.output,
                args.candidate_id,
                args.run_dir,
                args.runtime,
                args.api_pid,
                args.nginx_pid,
            )
        elif args.command == "write-active-metadata":
            write_active_metadata(
                args.output,
                args.candidate_id,
                args.sha,
                args.run_dir,
                args.runtime,
                args.api_pid,
                args.nginx_pid,
            )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
