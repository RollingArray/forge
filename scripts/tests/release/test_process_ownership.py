"""
FORGE Candidate Process Ownership Tests

Author:
-------
Ranjoy Sen

Purpose:
--------
Verifies candidate process ownership checks and safe cleanup validation.

Responsibilities:
-----------------
- Test candidate runtime metadata validation.
- Verify API and Nginx process ownership.
- Test handling of missing or invalid process metadata.
- Ensure unverified processes are not treated as candidate-owned.
"""


import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.release import process_ownership as ownership


def build_candidate(tmp_path: Path, *, with_metadata: bool = True):
    test_runs = tmp_path / "test-runs"
    run_dir = test_runs / "candidate-run"
    candidate_dir = tmp_path / "candidates" / "candidate-1"
    runtime = run_dir / "runtime" / "forge-deployment"

    run_dir.mkdir(parents=True)
    runtime.mkdir(parents=True)
    candidate_dir.mkdir(parents=True)

    archive = candidate_dir / "deployment.zip"
    archive.write_bytes(b"test deployment archive")

    import hashlib

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()

    (candidate_dir / "manifest.json").write_text(json.dumps({
        "candidate_id": "candidate-1",
        "archive": archive.name,
        "sha256": digest,
    }))

    (candidate_dir / "SHA256SUMS").write_text(
        f"{digest}  {archive.name}\n"
    )

    active_path = test_runs / "active.json"
    active_path.write_text(json.dumps({
        "candidate_id": "candidate-1",
        "sha256": digest,
        "run_dir": str(run_dir),
    }))

    if with_metadata:
        (run_dir / "runtime-processes.json").write_text(json.dumps({
            "candidate_id": "candidate-1",
            "run_dir": str(run_dir),
            "runtime": str(runtime),
            "api_pid": 12345,
            "nginx_pid": 12346,
            "api_port": 18875,
            "nginx_port": 18876,
        }))

    return test_runs, run_dir, candidate_dir, active_path, runtime


def test_resolves_valid_modern_runtime_metadata(tmp_path: Path):
    test_runs, run_dir, _, active_path, runtime = build_candidate(tmp_path)

    result = ownership.resolve_candidate_processes(active_path, test_runs)

    assert result == (
        "candidate-1",
        run_dir.resolve(),
        runtime.resolve(),
        12345,
        12346,
    )


def test_rejects_runtime_metadata_with_wrong_candidate_id(tmp_path: Path):
    test_runs, run_dir, _, active_path, _ = build_candidate(tmp_path)

    metadata_path = run_dir / "runtime-processes.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["candidate_id"] = "another-candidate"
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(ValueError, match="candidate ID"):
        ownership.resolve_candidate_processes(active_path, test_runs)


def test_rejects_runtime_metadata_with_wrong_runtime_path(tmp_path: Path):
    test_runs, run_dir, _, active_path, _ = build_candidate(tmp_path)

    metadata_path = run_dir / "runtime-processes.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["runtime"] = str(tmp_path / "unrelated-runtime")
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(ValueError, match="process path"):
        ownership.resolve_candidate_processes(active_path, test_runs)


def test_rejects_invalid_process_pids(tmp_path: Path):
    test_runs, run_dir, _, active_path, _ = build_candidate(tmp_path)

    metadata_path = run_dir / "runtime-processes.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["api_pid"] = True
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(ValueError, match="PIDs are invalid"):
        ownership.resolve_candidate_processes(active_path, test_runs)


def test_rejects_candidate_archive_checksum_mismatch(tmp_path: Path):
    test_runs, _, candidate_dir, active_path, _ = build_candidate(tmp_path)

    (candidate_dir / "deployment.zip").write_bytes(b"tampered archive")

    with pytest.raises(ValueError, match="artifact verification failed"):
        ownership.resolve_candidate_processes(active_path, test_runs)


def test_rejects_run_directory_outside_test_runs(tmp_path: Path):
    test_runs, _, _, active_path, _ = build_candidate(tmp_path)

    active = json.loads(active_path.read_text())
    active["run_dir"] = str(tmp_path / "outside")
    active_path.write_text(json.dumps(active))

    with pytest.raises(ValueError, match="outside"):
        ownership.resolve_candidate_processes(active_path, test_runs)


def test_discovers_valid_legacy_candidate_processes(tmp_path: Path):
    test_runs, run_dir, _, active_path, runtime = build_candidate(
        tmp_path,
        with_metadata=False,
    )

    commands = {
        "12345": (
            f"{runtime}/.venv/bin/python -m uvicorn app.main:app "
            "--host 127.0.0.1 --port 18875"
        ),
        "12346": (
            f"nginx: master process nginx -p {run_dir}/nginx/ "
            f"-c {run_dir}/nginx/nginx.conf -g daemon off;"
        ),
        "12347": "nginx: worker process",
    }

    with (
        patch.object(ownership, "listeners", side_effect=[
            ["12345"],
            ["12346", "12347"],
        ]),
        patch.object(ownership, "command_for", side_effect=lambda pid: commands[str(pid)]),
        patch.object(ownership, "parent_for", return_value="12346"),
    ):
        result = ownership.resolve_candidate_processes(active_path, test_runs)

    assert result == (
        "candidate-1",
        run_dir.resolve(),
        runtime.resolve(),
        12345,
        12346,
    )


def test_rejects_unrelated_legacy_api_listener(tmp_path: Path):
    test_runs, _, _, active_path, _ = build_candidate(
        tmp_path,
        with_metadata=False,
    )

    with patch.object(ownership, "listeners", side_effect=[
        ["22222"],
        ["12346"],
    ]), patch.object(
        ownership,
        "command_for",
        return_value="/usr/bin/python unrelated-service --port 18875",
    ):
        with pytest.raises(ValueError, match="not owned"):
            ownership.resolve_candidate_processes(active_path, test_runs)


def test_rejects_unverified_legacy_nginx_worker(tmp_path: Path):
    test_runs, run_dir, _, active_path, runtime = build_candidate(
        tmp_path,
        with_metadata=False,
    )

    commands = {
        "12345": (
            f"{runtime}/.venv/bin/python -m uvicorn app.main:app --port 18875"
        ),
        "12346": (
            f"nginx: master process nginx -p {run_dir}/nginx/ "
            f"-c {run_dir}/nginx/nginx.conf"
        ),
        "99999": "unrelated process",
    }

    with (
        patch.object(ownership, "listeners", side_effect=[
            ["12345"],
            ["12346", "99999"],
        ]),
        patch.object(ownership, "command_for", side_effect=lambda pid: commands[str(pid)]),
        patch.object(ownership, "parent_for", return_value="1"),
    ):
        with pytest.raises(ValueError, match="unverified listener"):
            ownership.resolve_candidate_processes(active_path, test_runs)
