"""Evidence generation and release-gate recording for FORGE."""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from pathlib import Path


def generate_pytest_summary(report_path, log_path, summary_path):
    report_path = Path(report_path)
    log_path = Path(log_path)
    summary_path = Path(summary_path)

    if not report_path.is_file():
        raise ValueError("Pytest JUnit report is missing.")
    if not log_path.is_file():
        raise ValueError("Pytest console log is missing.")

    root = ET.parse(report_path).getroot()

    test_cases = []
    for case in root.iter():
        if case.tag.rsplit("}", 1)[-1] != "testcase":
            continue

        outcome = next(
            (
                child.tag.rsplit("}", 1)[-1]
                for child in case
                if child.tag.rsplit("}", 1)[-1]
                in {"failure", "error", "skipped"}
            ),
            None,
        )

        status = (
            "SKIPPED" if outcome == "skipped"
            else "FAILED" if outcome in {"failure", "error"}
            else "PASSED"
        )

        test_cases.append({
            "classname": case.get("classname", ""),
            "name": case.get("name", ""),
            "time_seconds": float(case.get("time", 0)),
            "status": status,
        })

    tests = len(test_cases)
    failures = 0
    errors = 0
    skipped = 0
    passed = 0

    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "testcase":
            continue

        outcome_tags = {
            child.tag.rsplit("}", 1)[-1]
            for child in element
        }

        if "error" in outcome_tags:
            errors += 1
        elif "failure" in outcome_tags:
            failures += 1
        elif "skipped" in outcome_tags:
            skipped += 1
        else:
            passed += 1

    duration = sum(case["time_seconds"] for case in test_cases)

    log_text = log_path.read_text(errors="replace")

    warning_match = re.search(
        r"\b(\d+)\s+warnings?\s+in\s+[\d.]+s\b",
        log_text,
    )
    warning_count = int(warning_match.group(1)) if warning_match else 0

    warning_details = []
    start = re.search(
        r"=+ warnings summary =+\s*",
        log_text,
        re.IGNORECASE,
    )

    if start:
        remainder = log_text[start.end():]
        end = re.search(r"\n-- Docs:", remainder)
        section = remainder[:end.start()] if end else remainder
        warning_details = [
            line.rstrip()
            for line in section.splitlines()
            if line.strip()
        ]

    summary = {
        "status": "PASSED" if tests > 0 and passed == tests else "FAILED",
        "framework": "pytest",
        "discovered": tests,
        "passed": passed,
        "failed": failures + errors,
        "errors": errors,
        "skipped": skipped,
        "flaky": 0,
        "unexecuted": 0,
        "duration_seconds": round(duration, 3),
        "warning_count": warning_count,
        "warning_details": warning_details,
        "tests": test_cases,
        "report": "backend-pytest.xml",
        "log": "backend-pytest.log",
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    print(f"Backend Pytest: {passed}/{tests} PASSED")
    print(f"Duration: {duration:.3f}s | Warnings: {warning_count}")

    if len(test_cases) != tests:
        raise ValueError(
            "Pytest test-case inventory does not match JUnit discovery."
        )

    if tests < 1 or passed != tests or failures or errors or skipped:
        raise ValueError(
            "Backend Pytest did not meet the 100% release requirement."
        )

    return summary


def record_e2e_failure(
    active_path,
    run_dir,
    candidate_id,
    sha,
    started_at,
    failed_stage,
):
    completed_at = datetime.now(timezone.utc).isoformat()

    result = {
        "candidate_id": candidate_id,
        "sha256": sha,
        "status": "FAILED",
        "failed_stage": failed_stage,
        "started_at": started_at,
        "completed_at": completed_at,
        "run_dir": str(run_dir),
    }

    active_path = Path(active_path)
    run_dir = Path(run_dir)

    active_path.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    active_path.write_text(json.dumps(result, indent=2) + "\n")
    (run_dir / "release-gate.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )

    return result


def record_e2e_pass(
    active_path,
    run_dir,
    candidate_id,
    sha,
    started_at,
):
    run = Path(run_dir)

    automated = json.loads(
        (run / "reports/automated-summary.json").read_text()
    )
    real_email = json.loads(
        (run / "reports/real-email-summary.json").read_text()
    )

    manifest_path = (
        run.parents[1] / "candidates" / candidate_id / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    backend_pytest = manifest.get("backend_pytest")

    if (
        not isinstance(backend_pytest, dict)
        or backend_pytest.get("status") != "PASSED"
    ):
        raise ValueError(
            "Backend Pytest evidence is missing or has not passed."
        )

    result = {
        "candidate_id": candidate_id,
        "sha256": sha,
        "status": "PASSED",
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "automated_tests_expected": automated["discovered"],
        "automated_tests_status": "PASSED",
        "real_email_tests_expected": real_email["discovered"],
        "real_email_test_status": "PASSED",
        "backend_pytest": backend_pytest,
        "backend_pytest_status": "PASSED",
        "backend_pytest_expected": backend_pytest["discovered"],
        "automated_e2e": automated,
        "real_email_e2e": real_email,
        "real_email_completion": (
            "User completed visible browser verification"
        ),
        "run_dir": str(run_dir),
        "evidence_dir": str(run / "evidence"),
    }

    active_path = Path(active_path)
    active_path.parent.mkdir(parents=True, exist_ok=True)

    active_path.write_text(json.dumps(result, indent=2) + "\n")
    (run / "release-gate.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="FORGE release evidence operations."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    pytest_parser = commands.add_parser("pytest-summary")
    pytest_parser.add_argument("--report", required=True)
    pytest_parser.add_argument("--log", required=True)
    pytest_parser.add_argument("--output", required=True)

    failure_parser = commands.add_parser("e2e-failure")
    failure_parser.add_argument("--active", required=True)
    failure_parser.add_argument("--run-dir", required=True)
    failure_parser.add_argument("--candidate-id", required=True)
    failure_parser.add_argument("--sha", required=True)
    failure_parser.add_argument("--started-at", required=True)
    failure_parser.add_argument("--failed-stage", required=True)

    pass_parser = commands.add_parser("e2e-pass")
    pass_parser.add_argument("--active", required=True)
    pass_parser.add_argument("--run-dir", required=True)
    pass_parser.add_argument("--candidate-id", required=True)
    pass_parser.add_argument("--sha", required=True)
    pass_parser.add_argument("--started-at", required=True)

    args = parser.parse_args()

    try:
        if args.command == "pytest-summary":
            generate_pytest_summary(
                args.report,
                args.log,
                args.output,
            )
        elif args.command == "e2e-failure":
            record_e2e_failure(
                args.active,
                args.run_dir,
                args.candidate_id,
                args.sha,
                args.started_at,
                args.failed_stage,
            )
        elif args.command == "e2e-pass":
            record_e2e_pass(
                args.active,
                args.run_dir,
                args.candidate_id,
                args.sha,
                args.started_at,
            )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
