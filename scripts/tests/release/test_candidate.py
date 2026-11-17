import json
import stat
from pathlib import Path

import pytest

from scripts.forge_release.candidate import (
    create_manifest,
    write_active_metadata,
    write_runtime_metadata,
)


def valid_pytest_summary():
    return {
        "status": "PASSED",
        "discovered": 531,
        "passed": 531,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "flaky": 0,
        "unexecuted": 0,
    }


def test_creates_candidate_manifest(tmp_path: Path):
    archive = tmp_path / "deployment.zip"
    archive.write_bytes(b"test archive")

    summary_path = tmp_path / "pytest-summary.json"
    summary_path.write_text(json.dumps(valid_pytest_summary()))

    manifest_path = tmp_path / "candidate" / "manifest.json"

    result = create_manifest(
        manifest_path,
        "candidate-1",
        "abc123",
        archive,
        "commit123",
        summary_path,
    )

    saved = json.loads(manifest_path.read_text())

    assert saved == result
    assert saved["candidate_id"] == "candidate-1"
    assert saved["git_commit"] == "commit123"
    assert saved["archive"] == "deployment.zip"
    assert saved["sha256"] == "abc123"
    assert saved["size_bytes"] == len(b"test archive")
    assert saved["backend_pytest"] == valid_pytest_summary()
    assert saved["created_at"]


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"status": "FAILED"}, "did not pass"),
        ({"discovered": 0, "passed": 0}, "discovery count"),
        ({"passed": 530}, "passed count"),
        ({"failed": 1}, "failed count"),
        ({"errors": 1}, "errors count"),
        ({"skipped": 1}, "skipped count"),
        ({"flaky": 1}, "flaky count"),
        ({"unexecuted": 1}, "unexecuted count"),
        ({"discovered": True, "passed": True}, "discovery count"),
    ],
)
def test_rejects_invalid_pytest_evidence(tmp_path: Path, changes, message):
    archive = tmp_path / "deployment.zip"
    archive.write_bytes(b"test archive")

    summary = valid_pytest_summary()
    summary.update(changes)

    summary_path = tmp_path / "pytest-summary.json"
    summary_path.write_text(json.dumps(summary))

    with pytest.raises(ValueError, match=message):
        create_manifest(
            tmp_path / "manifest.json",
            "candidate-1",
            "abc123",
            archive,
            "commit123",
            summary_path,
        )


def test_rejects_missing_candidate_archive(tmp_path: Path):
    summary_path = tmp_path / "pytest-summary.json"
    summary_path.write_text(json.dumps(valid_pytest_summary()))

    with pytest.raises(ValueError, match="archive does not exist"):
        create_manifest(
            tmp_path / "manifest.json",
            "candidate-1",
            "abc123",
            tmp_path / "missing.zip",
            "commit123",
            summary_path,
        )


def test_writes_runtime_metadata_atomically_with_restricted_permissions(
    tmp_path: Path,
):
    run_dir = tmp_path / "candidate-run"
    runtime = run_dir / "runtime" / "forge-deployment"
    runtime.mkdir(parents=True)

    output = run_dir / "runtime-processes.json"

    result = write_runtime_metadata(
        output,
        "candidate-1",
        run_dir,
        runtime,
        12345,
        12346,
    )

    saved = json.loads(output.read_text())

    assert saved == result
    assert saved["candidate_id"] == "candidate-1"
    assert saved["run_dir"] == str(run_dir.resolve())
    assert saved["runtime"] == str(runtime.resolve())
    assert saved["api_pid"] == 12345
    assert saved["nginx_pid"] == 12346
    assert saved["api_port"] == 18875
    assert saved["nginx_port"] == 18876
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert not output.with_suffix(".tmp").exists()


def test_writes_active_candidate_prepared_metadata(tmp_path: Path):
    run_dir = tmp_path / "candidate-run"
    runtime = run_dir / "runtime" / "forge-deployment"
    runtime.mkdir(parents=True)

    output = tmp_path / "test-runs" / "active.json"

    result = write_active_metadata(
        output,
        "candidate-1",
        "abc123",
        run_dir,
        runtime,
        12345,
        12346,
    )

    saved = json.loads(output.read_text())

    assert saved == result
    assert saved["candidate_id"] == "candidate-1"
    assert saved["sha256"] == "abc123"
    assert saved["status"] == "PREPARED"
    assert saved["run_dir"] == str(run_dir)
    assert saved["runtime"] == str(runtime)
    assert saved["api_pid"] == 12345
    assert saved["nginx_pid"] == 12346
    assert saved["api_url"] == "http://127.0.0.1:18875"
    assert saved["ui_url"] == "http://127.0.0.1:18876"
    assert saved["created_at"]
    assert not output.with_suffix(".tmp").exists()
