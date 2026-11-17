#!/usr/bin/env python3
"""
FORGE E2E Report Validator

Author:
-------
Ranjoy Sen

Purpose:
--------
Validates Playwright E2E reports and determines whether their results satisfy
the evidence requirements used by the FORGE release process.

Responsibilities:
-----------------
- Collect individual test results from Playwright report suites.
- Classify test outcomes and execution details.
- Validate report structure, results, and expected test coverage.
- Reconcile report counts and identify invalid or incomplete evidence.
- Provide self-tests and command-line validation results.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def collect_tests(suites):
    """Recursively collect individual tests from Playwright JSON suites."""
    collected = []

    for suite in suites:
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                collected.append({
                    "file": spec.get("file") or suite.get("file") or "",
                    "title": spec.get("title", ""),
                    "test": test,
                })

        collected.extend(collect_tests(suite.get("suites", [])))

    return collected


def classify_test(test):
    """Return the final Playwright outcome and execution details."""
    status = test.get("status")
    results = test.get("results", [])
    expected_status = test.get("expectedStatus", "passed")

    attempts = len(results)
    retries = [
        result for result in results
        if result.get("retry", 0) > 0
    ]

    if status == "skipped":
        outcome = "skipped"
    elif not results:
        outcome = "unexecuted"
    elif status == "flaky":
        outcome = "flaky"
    elif status == "unexpected":
        outcome = "failed"
    elif status == "expected":
        if retries:
            outcome = "flaky"
        elif results[-1].get("status") != expected_status:
            outcome = "failed"
        elif expected_status != "passed":
            outcome = "nonstandard_expected"
        else:
            outcome = "passed"
    else:
        outcome = "invalid"

    return {
        "outcome": outcome,
        "attempts": attempts,
        "retries": len(retries),
        "project": test.get("projectName", ""),
        "expected_status": expected_status,
    }


def validate_report(report):
    """Calculate report counts and determine release eligibility."""
    if not isinstance(report, dict):
        raise ValueError("Playwright report root must be a JSON object.")

    suites = report.get("suites")
    stats = report.get("stats")

    if not isinstance(suites, list) or not isinstance(stats, dict):
        raise ValueError("Playwright report is missing suites or stats.")

    entries = collect_tests(suites)
    if not entries:
        raise ValueError("Playwright report contains no test records.")

    outcomes = []
    details = []

    for entry in entries:
        result = classify_test(entry["test"])
        outcomes.append(result["outcome"])
        details.append({
            "file": entry["file"],
            "title": entry["title"],
            **result,
        })

    counts = Counter(outcomes)

    discovered = len(entries)
    passed = counts["passed"]
    failed = counts["failed"] + counts["invalid"]
    skipped = counts["skipped"]
    flaky = counts["flaky"]
    unexecuted = counts["unexecuted"]
    nonstandard_expected = counts["nonstandard_expected"]

    # Independently reconcile the individual records with Playwright stats.
    expected_stats = {
        "expected": passed + nonstandard_expected,
        "unexpected": failed + unexecuted,
        "flaky": flaky,
        "skipped": skipped,
    }

    reconciliation = {}
    for key, calculated in expected_stats.items():
        reported = stats.get(key)
        if not isinstance(reported, int):
            reconciliation[key] = {
                "reported": reported,
                "calculated": calculated,
                "matches": False,
            }
        else:
            reconciliation[key] = {
                "reported": reported,
                "calculated": calculated,
                "matches": reported == calculated,
            }

    summary_matches = all(
        item["matches"] for item in reconciliation.values()
    )

    # Release suites must contain ordinary passing tests only.
    eligible = (
        discovered > 0
        and passed == discovered
        and failed == 0
        and skipped == 0
        and flaky == 0
        and unexecuted == 0
        and nonstandard_expected == 0
        and summary_matches
        and not report.get("errors")
    )

    return {
        "eligible": eligible,
        "discovered": discovered,
        "executed": discovered - unexecuted - skipped,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "flaky": flaky,
        "unexecuted": unexecuted,
        "nonstandard_expected": nonstandard_expected,
        "playwright_stats": stats,
        "summary_reconciliation": reconciliation,
        "summary_matches": summary_matches,
        "report_errors": report.get("errors", []),
        "tests": details,
    }


def synthetic_report(test_statuses):
    """Build a minimal Playwright v2 JSON report for self-tests."""
    tests = []
    counts = Counter()

    for index, scenario in enumerate(test_statuses, start=1):
        status = scenario["status"]
        expected_status = scenario.get("expectedStatus", "passed")
        results = scenario.get("results", [])

        tests.append({
            "timeout": 1000,
            "annotations": [],
            "expectedStatus": expected_status,
            "projectName": "synthetic",
            "projectId": "synthetic",
            "status": status,
            "results": results,
        })

        if status == "expected":
            counts["expected"] += 1
        elif status == "unexpected":
            counts["unexpected"] += 1
        elif status == "flaky":
            counts["flaky"] += 1
        elif status == "skipped":
            counts["skipped"] += 1

    return {
        "suites": [{
            "title": "synthetic.spec.ts",
            "file": "synthetic.spec.ts",
            "line": 1,
            "column": 1,
            "specs": [{
                "title": f"Scenario {index}",
                "file": "synthetic.spec.ts",
                "line": index,
                "column": 1,
                "id": f"synthetic-{index}",
                "ok": True,
                "tags": [],
                "tests": [test],
            }]
        } for index, test in enumerate(tests, start=1)],
        "errors": [],
        "stats": {
            "expected": counts["expected"],
            "unexpected": counts["unexpected"],
            "flaky": counts["flaky"],
            "skipped": counts["skipped"],
        },
    }


def run_self_tests():
    passed_result = {
        "retry": 0,
        "status": "passed",
        "duration": 10,
        "errors": [],
    }

    failed_result = {
        "retry": 0,
        "status": "failed",
        "duration": 10,
        "errors": [{"message": "Synthetic failure"}],
    }

    retry_failed = {
        "retry": 0,
        "status": "failed",
        "duration": 10,
        "errors": [{"message": "Synthetic first attempt failure"}],
    }

    retry_passed = {
        "retry": 1,
        "status": "passed",
        "duration": 10,
        "errors": [],
    }

    scenarios = [
        (
            "clean pass",
            [{"status": "expected", "results": [passed_result]}],
            True,
        ),
        (
            "failed test",
            [{"status": "unexpected", "results": [failed_result]}],
            False,
        ),
        (
            "flaky retry",
            [{
                "status": "flaky",
                "results": [retry_failed, retry_passed],
            }],
            False,
        ),
        (
            "skipped test",
            [{"status": "skipped", "results": []}],
            False,
        ),
        (
            "unexecuted test",
            [{"status": "expected", "results": []}],
            False,
        ),
        (
            "inconsistent summary",
            [{"status": "expected", "results": [passed_result]}],
            False,
        ),
    ]

    for name, test_statuses, expected_eligible in scenarios:
        report = synthetic_report(test_statuses)

        if name == "inconsistent summary":
            report["stats"]["expected"] = 0

        result = validate_report(report)
        actual = result["eligible"]

        if actual != expected_eligible:
            print(
                f"FAIL: {name}: expected eligible={expected_eligible}, "
                f"got {actual}",
                file=sys.stderr,
            )
            return 1

        print(f"PASS: {name}")

    print("All validator self-tests passed.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate Playwright JSON reports for FORGE release gates."
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_tests()

    if not args.report:
        parser.error("Provide --report or use --self-test.")

    try:
        report = json.loads(args.report.read_text())
        result = validate_report(report)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    serialized = json.dumps(result, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n")
    else:
        print(serialized)

    print(
        f"Release eligibility: {'PASSED' if result['eligible'] else 'FAILED'}",
        file=sys.stderr,
    )
    print(
        "Discovered={discovered} Passed={passed} Failed={failed} "
        "Skipped={skipped} Flaky={flaky} Unexecuted={unexecuted}".format(
            **result
        ),
        file=sys.stderr,
    )

    return 0 if result["eligible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
