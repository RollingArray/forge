"""
FORGE Release Content Manager

Author:
-------
Ranjoy Sen

Purpose:
--------
Validates candidate evidence and prepares release information.

Responsibilities:
-----------------
- Validate candidate archive and release evidence.
- Collect backend and E2E validation results.
- Prepare candidate details for release communication.
"""


import argparse
from html import escape as html_escape
import json
import re
import shutil
import subprocess
import sys
import zipfile
from release.validation import (
    ValidationError,
    read_json as shared_read_json,
    sha256_file as shared_sha256_file,
    validate_candidate_artifacts,
    validate_e2e_summary,
    validate_pytest_evidence,
    validate_pytest_summary,
)
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ROOT / "dist" / "candidates"
TEST_RUNS = ROOT / "dist" / "test-runs"

def fail(message):
    raise SystemExit(f"ERROR: {message}")
def sha256_file(path):
    try:
        return shared_sha256_file(path)
    except ValidationError as exc:
        fail(str(exc))
def read_json(path):
    try:
        return shared_read_json(path)
    except ValidationError as exc:
        fail(str(exc))
def validate_candidate(candidate_id):
    candidate_dir = CANDIDATES / candidate_id
    run_dir = TEST_RUNS / candidate_id

    gate_path = run_dir / "release-gate.json"
    manifest_path = candidate_dir / "manifest.json"
    checksum_path = candidate_dir / "SHA256SUMS"

    for path in (gate_path, manifest_path, checksum_path):
        if not path.is_file():
            fail(f"Required release artifact is missing: {path}")

    gate = read_json(gate_path)
    manifest = read_json(manifest_path)

    if gate.get("candidate_id") != candidate_id:
        fail("Release gate candidate ID mismatch.")

    if gate.get("status") != "PASSED":
        fail("Release gate has not passed.")

    backend_pytest = gate.get("backend_pytest")
    manifest_pytest = manifest.get("backend_pytest")

    try:
        validate_pytest_summary(backend_pytest, "Backend Pytest release gate")
        validate_pytest_summary(
            manifest_pytest, "Backend Pytest candidate manifest"
        )
    except ValidationError as exc:
        fail(str(exc))

    if backend_pytest != manifest_pytest:
        fail("Backend Pytest evidence differs between manifest and release gate.")

    pytest_evidence_dir = run_dir / "evidence"
    try:
        pytest_evidence = validate_pytest_evidence(run_dir, backend_pytest)
    except ValidationError as exc:
        fail(str(exc))

    pytest_xml_path = pytest_evidence["xml_path"]
    pytest_log_path = pytest_evidence["log_path"]
    pytest_summary_path = pytest_evidence["summary_path"]
    retained_pytest = pytest_evidence["summary"]
    pytest_cases = backend_pytest["tests"]

    if gate.get("backend_pytest_status") != "PASSED":
        fail("Backend Pytest release gate did not pass.")
    if gate.get("backend_pytest_expected") != backend_pytest["discovered"]:
        fail("Backend Pytest count does not match its validated summary.")

    automated = gate.get("automated_e2e")
    real_email = gate.get("real_email_e2e")

    try:
        validate_e2e_summary(automated, "Automated E2E")
        validate_e2e_summary(real_email, "Real-email E2E")
    except ValidationError as exc:
        fail(str(exc))

    if gate.get("automated_tests_expected") != automated["discovered"]:
        fail("Automated E2E count does not match its validated report.")

    if gate.get("automated_tests_status") != "PASSED":
        fail("Automated E2E tests did not pass.")

    if gate.get("real_email_tests_expected") != real_email["discovered"]:
        fail("Real-email E2E count does not match its validated report.")

    if gate.get("real_email_test_status") != "PASSED":
        fail("Real-email E2E test did not pass.")

    if not gate.get("sha256"):
        fail("Release gate SHA-256 is missing.")

    try:
        candidate_artifacts = validate_candidate_artifacts(
            candidate_dir,
            candidate_id,
            expected_sha=gate["sha256"],
        )
    except ValidationError as exc:
        fail(str(exc))

    archive = candidate_artifacts["archive"]
    actual_sha = candidate_artifacts["sha256"]

    ai_config = None

    with zipfile.ZipFile(archive) as bundle:
        matches = [
            name for name in bundle.namelist()
            if name.endswith("/backend/api/config/ai.json")
        ]

        if len(matches) != 1:
            fail("Could not uniquely identify AI configuration in candidate ZIP.")

        ai_config = json.loads(bundle.read(matches[0]))

    ai = ai_config.get("provider_config", ai_config)
    endpoint = (
        ai.get("base_url")
        or ai.get("endpoint")
        or "Not specified in candidate configuration"
    )
    model = (
        ai.get("model")
        or "Not specified in candidate configuration"
    )

    evidence_dir = gate.get("evidence_dir") or str(run_dir / "evidence")

    commit = manifest.get("git_commit", "Not recorded")

    backend_count = backend_pytest["discovered"]
    backend_duration = backend_pytest["duration_seconds"]
    backend_warning_count = backend_pytest["warning_count"]
    backend_warning_details = backend_pytest["warning_details"]

    pytest_case_lines_list = []
    pytest_html_rows = []
    for case in backend_pytest["tests"]:
        test_name = f'{case["classname"]}::{case["name"]}'
        duration_text = f'{case.get("time_seconds", 0):.3f}s'
        pytest_case_lines_list.append(
            f'[PYTEST] [PASSED] {test_name} ({duration_text})'
        )
        pytest_html_rows.append(
            "<tr>"
            f"<td>{html_escape(case['classname'])}</td>"
            f"<td>{html_escape(case['name'])}</td>"
            f"<td>{html_escape(duration_text)}</td>"
            "<td>PASSED</td>"
            "</tr>"
        )

    pytest_case_lines = "\n".join(pytest_case_lines_list)
    pytest_html_case_rows = "\n".join(pytest_html_rows)
    warning_text = (
        "\n".join(backend_warning_details)
        if backend_warning_details
        else "No warning details were recorded."
    )
    warning_text_h = html_escape(warning_text)

    automated_count = automated["discovered"]
    real_email_count = real_email["discovered"]
    total_count = backend_count + automated_count + real_email_count

    def format_test_cases(summary, fallback_prefix):
        cases = []

        for sequence, item in enumerate(summary.get("tests", []), start=1):
            description = item.get("title") or "Untitled Playwright test"

            if fallback_prefix == "REAL-EMAIL":
                test_id = f"REAL-EMAIL-{sequence:02d}"
                if description.startswith("REAL EMAIL E2E:"):
                    description = description.split(":", 1)[1].strip()
            else:
                identified = re.match(
                    r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*)$",
                    description,
                )
                if identified:
                    test_id = identified.group(1)
                    description = identified.group(2).strip()

                    if test_id == "LG-16":
                        status_match = re.search(
                            r"HTTP\s*(400|403|404)", description
                        )
                        if status_match:
                            test_id = f"LG-16-{status_match.group(1)}"
                else:
                    test_id = f"PW-{sequence:02d}"

            description = re.sub(r"\s+", " ", description).strip()
            cases.append(f"[{test_id}] [PASSED] {description}")

        if len(cases) != summary.get("passed"):
            fail(f"{fallback_prefix} test inventory does not match its validated count.")

        return cases

    automated_cases = format_test_cases(automated, "TC")
    real_email_cases = format_test_cases(real_email, "REAL-EMAIL")
    all_cases = automated_cases + real_email_cases
    test_case_lines = "\n".join(all_cases)
    html_test_case_rows = "\n".join(
        f"<tr><td>{html_escape(case)}</td></tr>"
        for case in all_cases
    )

    subject = (
        f"FORGE | Release Candidate | "
        f"{total_count}/{total_count} Tests Passed | {candidate_id}"
    )

    candidate_h = html_escape(candidate_id)
    commit_h = html_escape(str(commit))
    sha_h = html_escape(actual_sha)
    archive_h = html_escape(archive.name)
    model_h = html_escape(str(model))

    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    pytest_report_path = reports_dir / "backend-pytest-report.html"
    e2e_report_path = reports_dir / "e2e-validation-report.html"

    common_style = """
    <style>
      body { font-family: Arial, Helvetica, sans-serif; color: #263445;
             margin: 32px; line-height: 1.5; }
      h1 { color: #183B63; margin-bottom: 6px; }
      h2 { color: #183B63; margin-top: 30px; }
      .muted { color: #64748b; }
      .summary { display: flex; flex-wrap: wrap; gap: 12px;
                 margin: 22px 0; }
      .metric { border: 1px solid #d7dee8; border-radius: 8px;
                padding: 12px 16px; min-width: 130px; }
      .metric strong { display: block; font-size: 22px; color: #183B63; }
      .pass { color: #18794e; font-weight: bold; }
      table { border-collapse: collapse; width: 100%; margin-top: 12px; }
      th, td { border: 1px solid #d7dee8; padding: 8px;
               text-align: left; vertical-align: top; }
      th { background: #eaf0f6; }
      tr:nth-child(even) { background: #f8fafc; }
      code { overflow-wrap: anywhere; }
      pre { white-space: pre-wrap; overflow-wrap: anywhere;
            background: #f5f7fa; padding: 14px; border-radius: 6px; }
      @media print { body { margin: 12px; } }
    </style>
    """

    pytest_html_rows = []
    for case in pytest_cases:
        pytest_html_rows.append(
            "<tr>"
            f"<td>{html_escape(str(case['classname']))}</td>"
            f"<td>{html_escape(str(case['name']))}</td>"
            f"<td>{float(case.get('time_seconds', 0)):.3f}s</td>"
            '<td class="pass">PASSED</td>'
            "</tr>"
        )

    warning_html = (
        html_escape("\n".join(backend_warning_details))
        if backend_warning_details
        else "No warning details were recorded."
    )

    pytest_report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FORGE Backend Pytest Report</title>
{common_style}
</head>
<body>
<h1>FORGE Backend Pytest Report</h1>
<p class="muted">Release candidate: {candidate_h} |
Git commit: <code>{commit_h}</code></p>

<div class="summary">
  <div class="metric"><strong>{backend_count}/{backend_count}</strong>Tests passed</div>
  <div class="metric"><strong>{backend_duration:.3f}s</strong>Execution time</div>
  <div class="metric"><strong>{backend_warning_count}</strong>Warnings</div>
  <div class="metric"><strong class="pass">PASSED</strong>Release result</div>
</div>

<h2>Execution summary</h2>
<table>
<tr><th>Metric</th><th>Result</th></tr>
<tr><td>Framework</td><td>pytest</td></tr>
<tr><td>Discovered</td><td>{backend_count}</td></tr>
<tr><td>Passed</td><td>{backend_count}</td></tr>
<tr><td>Failed</td><td>0</td></tr>
<tr><td>Errors</td><td>0</td></tr>
<tr><td>Skipped</td><td>0</td></tr>
<tr><td>Flaky</td><td>0</td></tr>
<tr><td>Unexecuted</td><td>0</td></tr>
</table>

<h2>Warnings</h2>
<p>These warnings were recorded during the regression run. They did not
cause test failures.</p>
<pre>{warning_html}</pre>

<h2>Individual test results ({backend_count})</h2>
<table>
<tr><th>Test module</th><th>Test case</th><th>Duration</th><th>Result</th></tr>
{"".join(pytest_html_rows)}
</table>
</body>
</html>
"""

    e2e_html_rows = []
    for case in all_cases:
        match = re.fullmatch(
            r"\[([^\]]+)\]\s+\[([^\]]+)\]\s+(.+)",
            case,
        )
        if not match:
            fail(f"Unexpected E2E test inventory format: {case}")

        test_id, result, scenario = match.groups()
        e2e_html_rows.append(
            "<tr>"
            f"<td>{html_escape(test_id)}</td>"
            f"<td>{html_escape(scenario)}</td>"
            f'<td class="pass">{html_escape(result)}</td>'
            "</tr>"
        )

    e2e_report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FORGE E2E Validation Report</title>
{common_style}
</head>
<body>
<h1>FORGE End-to-End Validation Report</h1>
<p class="muted">Release candidate: {candidate_h} |
Git commit: <code>{commit_h}</code></p>

<div class="summary">
  <div class="metric"><strong>{automated_count}/{automated_count}</strong>Automated E2E passed</div>
  <div class="metric"><strong>{real_email_count}/{real_email_count}</strong>Real-email E2E passed</div>
  <div class="metric"><strong>{len(all_cases)}/{len(all_cases)}</strong>Total E2E passed</div>
  <div class="metric"><strong class="pass">PASSED</strong>Release result</div>
</div>

<h2>Validation summary</h2>
<table>
<tr><th>Validation stage</th><th>Discovered</th><th>Passed</th>
<th>Failed</th><th>Skipped</th><th>Flaky</th><th>Unexecuted</th></tr>
<tr><td>Automated Playwright E2E</td>
<td>{automated['discovered']}</td><td>{automated['passed']}</td>
<td>{automated['failed']}</td><td>{automated['skipped']}</td>
<td>{automated['flaky']}</td><td>{automated['unexecuted']}</td></tr>
<tr><td>Real-email E2E</td>
<td>{real_email['discovered']}</td><td>{real_email['passed']}</td>
<td>{real_email['failed']}</td><td>{real_email['skipped']}</td>
<td>{real_email['flaky']}</td><td>{real_email['unexecuted']}</td></tr>
</table>

<h2>Validated E2E test cases ({len(all_cases)})</h2>
<table>
<tr><th>Test ID</th><th>Test scenario</th><th>Result</th></tr>
{"".join(e2e_html_rows)}
</table>

<h2>Release candidate</h2>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Candidate</td><td>{candidate_h}</td></tr>
<tr><td>Git commit</td><td><code>{commit_h}</code></td></tr>
<tr><td>Deployment archive</td><td>{archive_h}</td></tr>
<tr><td>SHA-256</td><td><code>{sha_h}</code></td></tr>
<tr><td>AI model</td><td>{model_h}</td></tr>
</table>
</body>
</html>
"""

    pytest_report_path.write_text(pytest_report_html, encoding="utf-8")
    e2e_report_path.write_text(e2e_report_html, encoding="utf-8")

    for report_path in (pytest_report_path, e2e_report_path):
        if not report_path.is_file() or report_path.stat().st_size == 0:
            fail(f"HTML report generation failed: {report_path}")

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<body style="font-family: Arial, Helvetica, sans-serif; color: #263445;
             font-size: 13px; line-height: 1.5;">
<p>Hello,</p>

<p>The FORGE release candidate has completed validation. All release gates
passed successfully.</p>

<h3 style="color: #183B63;">Release summary</h3>
<table cellpadding="7" cellspacing="0" border="1"
       style="border-collapse: collapse; border-color: #D7DEE8;">
<tr><td><b>Candidate</b></td><td>{candidate_h}</td></tr>
<tr><td><b>Git commit</b></td><td>{commit_h}</td></tr>
<tr><td><b>Backend Pytest</b></td><td>{backend_count}/{backend_count} PASSED</td></tr>
<tr><td><b>Automated E2E</b></td><td>{automated_count}/{automated_count} PASSED</td></tr>
<tr><td><b>Real-email E2E</b></td><td>{real_email_count}/{real_email_count} PASSED</td></tr>
<tr><td><b>Overall validation</b></td><td><b>{total_count}/{total_count} PASSED</b></td></tr>
<tr><td><b>Release gate</b></td><td><b>PASSED</b></td></tr>
</table>

<h3 style="color: #183B63;">Attachments</h3>
<ol>
<li>{archive_h} - validated deployment package</li>
<li>{html_escape(e2e_report_path.name)} - E2E test results and scenario inventory</li>
<li>{html_escape(pytest_report_path.name)} - backend regression results and warning details</li>
</ol>

<p>The attached HTML reports contain the detailed test inventories and
execution evidence. The deployment ZIP checksum is:</p>
<p><code>{sha_h}</code></p>

<p>Please review the package and reports before release.</p>
</body>
</html>"""

    body = f"""Hello,

The FORGE release candidate has completed validation. All release gates passed.

RELEASE SUMMARY
Candidate: {candidate_id}
Git commit: {commit}
Backend Pytest: {backend_count}/{backend_count} PASSED
Automated E2E: {automated_count}/{automated_count} PASSED
Real-email E2E: {real_email_count}/{real_email_count} PASSED
Overall validation: {total_count}/{total_count} PASSED
Release gate: PASSED

ATTACHMENTS
1. {archive.name} - validated deployment package
2. {e2e_report_path.name} - E2E validation report
3. {pytest_report_path.name} - backend Pytest report

The attached HTML reports contain the detailed test inventories, execution
durations and warning details.

SHA-256: {actual_sha}

Please review the package and reports before release.
"""

    return {
        "candidate_id": candidate_id,
        "candidate_dir": candidate_dir,
        "run_dir": run_dir,
        "archive": archive,
        "sha256": actual_sha,
        "subject": subject,
        "body": body,
        "html_body": html_body,
        "pytest_report": pytest_report_path,
        "e2e_report": e2e_report_path,
        "evidence_dir": evidence_dir,
        "endpoint": endpoint,
        "model": model,
        "backend_count": backend_count,
        "automated_count": automated_count,
        "real_email_count": real_email_count,
        "total_count": total_count,
    }
