import json
from pathlib import Path

import pytest

from scripts.forge_release.evidence import (
    generate_pytest_summary,
    record_e2e_failure,
    record_e2e_pass,
)


def test_generates_valid_pytest_summary(tmp_path: Path):
    report = tmp_path / "pytest.xml"
    log = tmp_path / "pytest.log"
    output = tmp_path / "summary.json"

    report.write_text("""<?xml version="1.0"?>
<testsuites>
  <testsuite tests="2" failures="0" errors="0" skipped="0">
    <testcase classname="sample" name="test_one" time="0.10"/>
    <testcase classname="sample" name="test_two" time="0.20"/>
  </testsuite>
</testsuites>
""")
    log.write_text("2 passed, 1 warning in 0.30s\n")

    result = generate_pytest_summary(report, log, output)

    assert result["status"] == "PASSED"
    assert result["discovered"] == 2
    assert result["passed"] == 2
    assert result["failed"] == 0
    assert result["warning_count"] == 1
    assert result["duration_seconds"] == 0.3
    assert json.loads(output.read_text()) == result


def test_rejects_pytest_failure(tmp_path: Path):
    report = tmp_path / "pytest.xml"
    log = tmp_path / "pytest.log"
    output = tmp_path / "summary.json"

    report.write_text("""<testsuites>
  <testsuite tests="2" failures="1" errors="0" skipped="0">
    <testcase classname="sample" name="test_one" time="0.1">
      <failure message="failed">assert False</failure>
    </testcase>
    <testcase classname="sample" name="test_two" time="0.2"/>
  </testsuite>
</testsuites>
""")
    log.write_text("1 failed, 1 passed in 0.30s\n")

    with pytest.raises(ValueError, match="100% release requirement"):
        generate_pytest_summary(report, log, output)

    summary = json.loads(output.read_text())
    assert summary["status"] == "FAILED"
    assert summary["discovered"] == 2
    assert summary["failed"] == 1
    assert summary["passed"] == 1


def test_rejects_missing_pytest_report(tmp_path: Path):
    with pytest.raises(ValueError, match="JUnit report is missing"):
        generate_pytest_summary(
            tmp_path / "missing.xml",
            tmp_path / "pytest.log",
            tmp_path / "summary.json",
        )


def test_records_e2e_failure(tmp_path: Path):
    active = tmp_path / "test-runs" / "active.json"
    run_dir = tmp_path / "test-runs" / "candidate-1"

    result = record_e2e_failure(
        active,
        run_dir,
        "candidate-1",
        "abc123",
        "2026-11-17T10:00:00+00:00",
        "automated-e2e",
    )

    assert result["status"] == "FAILED"
    assert result["failed_stage"] == "automated-e2e"
    assert result["candidate_id"] == "candidate-1"
    assert json.loads(active.read_text()) == result
    assert json.loads((run_dir / "release-gate.json").read_text()) == result


def test_records_successful_e2e_release_gate(tmp_path: Path):
    test_runs = tmp_path / "test-runs"
    run_dir = test_runs / "candidate-1"
    candidate_dir = tmp_path / "candidates" / "candidate-1"

    (run_dir / "reports").mkdir(parents=True)
    (run_dir / "evidence").mkdir()
    candidate_dir.mkdir(parents=True)

    automated = {"discovered": 99, "passed": 99, "status": "PASSED"}
    real_email = {"discovered": 1, "passed": 1, "status": "PASSED"}
    backend = {"discovered": 531, "passed": 531, "status": "PASSED"}

    (run_dir / "reports" / "automated-summary.json").write_text(
        json.dumps(automated)
    )
    (run_dir / "reports" / "real-email-summary.json").write_text(
        json.dumps(real_email)
    )
    (candidate_dir / "manifest.json").write_text(
        json.dumps({"backend_pytest": backend})
    )

    active = test_runs / "active.json"

    result = record_e2e_pass(
        active,
        run_dir,
        "candidate-1",
        "abc123",
        "2026-11-17T10:00:00+00:00",
    )

    assert result["status"] == "PASSED"
    assert result["automated_tests_expected"] == 99
    assert result["real_email_tests_expected"] == 1
    assert result["backend_pytest_expected"] == 531
    assert result["real_email_completion"] == (
        "User completed visible browser verification"
    )
    assert json.loads(active.read_text()) == result
    assert json.loads((run_dir / "release-gate.json").read_text()) == result


def test_rejects_success_when_backend_pytest_evidence_is_missing(tmp_path: Path):
    test_runs = tmp_path / "test-runs"
    run_dir = test_runs / "candidate-1"
    candidate_dir = tmp_path / "candidates" / "candidate-1"

    (run_dir / "reports").mkdir(parents=True)
    candidate_dir.mkdir(parents=True)

    (run_dir / "reports" / "automated-summary.json").write_text(
        json.dumps({"discovered": 99})
    )
    (run_dir / "reports" / "real-email-summary.json").write_text(
        json.dumps({"discovered": 1})
    )
    (candidate_dir / "manifest.json").write_text(
        json.dumps({"backend_pytest": {"status": "FAILED"}})
    )

    with pytest.raises(ValueError, match="Backend Pytest evidence"):
        record_e2e_pass(
            test_runs / "active.json",
            run_dir,
            "candidate-1",
            "abc123",
            "2026-11-17T10:00:00+00:00",
        )
