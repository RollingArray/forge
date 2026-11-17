#!/usr/bin/env python3
"""
FORGE Shared Release Validator

Author:
-------
Ranjoy Sen

Purpose:
--------
Provides reusable validation for candidate artifacts and release evidence.

Responsibilities:
-----------------
- Validate candidate archive contents and identity.
- Validate backend Pytest evidence.
- Validate Playwright E2E summaries.
- Provide shared validation utilities and error handling.
"""


import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


class ValidationError(ValueError):
    """Raised when release evidence fails validation."""


def read_json(path):
    """Read a JSON file and return its decoded value."""
    path = Path(path)

    if not path.is_file():
        raise ValidationError(f"Required JSON file is missing: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Cannot read valid JSON from {path}: {exc}") from exc


def sha256_file(path):
    """Calculate a file's SHA-256 digest without loading it entirely into memory."""
    path = Path(path)
    digest = hashlib.sha256()

    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValidationError(f"Cannot read file for SHA-256: {path}: {exc}") from exc

    return digest.hexdigest()


def validate_candidate_artifacts(candidate_dir, candidate_id, expected_sha=None):
    """
    Validate candidate identity, manifest, archive and SHA256SUMS.

    Returns the validated manifest, archive path and actual SHA-256 digest.
    """
    candidate_dir = Path(candidate_dir).resolve()

    if not candidate_id or Path(candidate_id).name != candidate_id:
        raise ValidationError("Candidate ID is empty or contains an invalid path.")

    if not candidate_dir.is_dir():
        raise ValidationError(f"Candidate directory is missing: {candidate_dir}")

    manifest_path = candidate_dir / "manifest.json"
    checksum_path = candidate_dir / "SHA256SUMS"

    manifest = read_json(manifest_path)

    if not isinstance(manifest, dict):
        raise ValidationError("Candidate manifest must be a JSON object.")

    if manifest.get("candidate_id") != candidate_id:
        raise ValidationError("Candidate manifest ID mismatch.")

    archive_name = manifest.get("archive")
    if (
        not isinstance(archive_name, str)
        or not archive_name
        or Path(archive_name).name != archive_name
    ):
        raise ValidationError("Candidate archive filename is invalid.")

    archive_path = candidate_dir / archive_name

    if not archive_path.is_file():
        raise ValidationError(f"Candidate archive is missing: {archive_path}")

    manifest_sha = manifest.get("sha256")
    if not isinstance(manifest_sha, str) or len(manifest_sha) != 64:
        raise ValidationError("Candidate manifest SHA-256 is missing or invalid.")

    actual_sha = sha256_file(archive_path)

    if actual_sha.lower() != manifest_sha.lower():
        raise ValidationError("Candidate archive SHA-256 does not match its manifest.")

    if expected_sha is not None and actual_sha.lower() != str(expected_sha).lower():
        raise ValidationError("Candidate archive SHA-256 does not match the expected value.")

    if not checksum_path.is_file():
        raise ValidationError(f"Candidate checksum file is missing: {checksum_path}")

    matching_checksum = False

    try:
        checksum_lines = checksum_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"Cannot read candidate checksum file: {exc}") from exc

    for line in checksum_lines:
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue

        recorded_sha = parts[0]
        recorded_name = parts[1].lstrip("*")

        if recorded_name == archive_name and recorded_sha.lower() == actual_sha.lower():
            matching_checksum = True
            break

    if not matching_checksum:
        raise ValidationError("SHA256SUMS does not verify the candidate archive.")

    return {
        "candidate_id": candidate_id,
        "candidate_dir": candidate_dir,
        "manifest": manifest,
        "archive": archive_path,
        "sha256": actual_sha,
    }


def validate_pytest_summary(summary, label="Backend Pytest"):
    """Validate the release requirements represented by a Pytest summary."""
    if not isinstance(summary, dict):
        raise ValidationError(f"{label} summary is missing or invalid.")

    if summary.get("status") != "PASSED":
        raise ValidationError(f"{label} did not pass.")

    discovered = summary.get("discovered")
    if not isinstance(discovered, int) or isinstance(discovered, bool) or discovered < 1:
        raise ValidationError(f"{label} discovery count is invalid.")

    if summary.get("passed") != discovered:
        raise ValidationError(f"{label} passed count does not match discovery.")

    for key in ("failed", "errors", "skipped", "flaky", "unexecuted"):
        if summary.get(key) != 0:
            raise ValidationError(f"{label} has nonzero {key} count.")

    tests = summary.get("tests")
    if not isinstance(tests, list) or len(tests) != discovered:
        raise ValidationError(f"{label} individual test inventory is missing or incomplete.")

    for case in tests:
        if not isinstance(case, dict):
            raise ValidationError(f"{label} inventory contains an invalid test record.")
        if not case.get("classname") or not case.get("name"):
            raise ValidationError(f"{label} inventory contains a test without a module or name.")
        if case.get("status") != "PASSED":
            raise ValidationError(f"{label} inventory contains a test that did not pass.")

    if not isinstance(summary.get("duration_seconds"), (int, float)):
        raise ValidationError(f"{label} duration is missing or invalid.")

    warning_count = summary.get("warning_count")
    if not isinstance(warning_count, int) or isinstance(warning_count, bool) or warning_count < 0:
        raise ValidationError(f"{label} warning count is missing or invalid.")

    if not isinstance(summary.get("warning_details"), list):
        raise ValidationError(f"{label} warning details are missing or invalid.")

    return summary


def validate_pytest_evidence(run_dir, expected_summary):
    """
    Validate the retained Pytest JSON summary and JUnit XML against the
    summary embedded in the release gate and candidate manifest.
    """
    run_dir = Path(run_dir)
    evidence_dir = run_dir / "evidence"

    xml_path = evidence_dir / "backend-pytest.xml"
    log_path = evidence_dir / "backend-pytest.log"
    summary_path = evidence_dir / "backend-pytest-summary.json"

    for path in (xml_path, log_path, summary_path):
        if not path.is_file():
            raise ValidationError(f"Backend Pytest evidence file is missing: {path}")

    validate_pytest_summary(expected_summary)

    retained_summary = read_json(summary_path)
    if retained_summary != expected_summary:
        raise ValidationError("Retained Pytest summary differs from the release gate.")

    try:
        root = ET.parse(xml_path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValidationError(f"Cannot parse retained Pytest JUnit report: {exc}") from exc

    junit_cases = [
        case
        for case in root.iter()
        if case.tag.rsplit("}", 1)[-1] == "testcase"
    ]

    discovered = expected_summary["discovered"]
    if len(junit_cases) != discovered:
        raise ValidationError("Retained JUnit test count differs from the release gate.")

    junit_inventory = []
    failures = 0
    errors = 0
    skipped = 0

    for case in junit_cases:
        classname = case.get("classname", "")
        name = case.get("name", "")

        if not classname or not name:
            raise ValidationError("JUnit report contains a test without a module or name.")

        junit_inventory.append((classname, name))

        outcome_tags = {
            child.tag.rsplit("}", 1)[-1]
            for child in case
        }

        if "error" in outcome_tags:
            errors += 1
        elif "failure" in outcome_tags:
            failures += 1
        elif "skipped" in outcome_tags:
            skipped += 1

    summary_inventory = sorted(
        (case["classname"], case["name"])
        for case in expected_summary["tests"]
    )

    if sorted(junit_inventory) != summary_inventory:
        raise ValidationError("Retained JUnit test inventory differs from the Pytest summary.")

    if failures or errors or skipped:
        raise ValidationError(
            "JUnit report contains failures, errors or skipped tests "
            f"({failures}/{errors}/{skipped})."
        )

    return {
        "summary": retained_summary,
        "junit_tests": len(junit_cases),
        "junit_failures": failures,
        "junit_errors": errors,
        "junit_skipped": skipped,
        "xml_path": xml_path,
        "log_path": log_path,
        "summary_path": summary_path,
    }


def validate_e2e_summary(summary, label="E2E"):
    """Validate a Playwright summary against FORGE release requirements."""
    if not isinstance(summary, dict):
        raise ValidationError(f"{label} validation summary is missing.")

    if summary.get("eligible") is not True:
        raise ValidationError(f"{label} report is not eligible.")

    discovered = summary.get("discovered")
    if not isinstance(discovered, int) or isinstance(discovered, bool) or discovered < 1:
        raise ValidationError(f"{label} discovered-test count is invalid.")

    if summary.get("passed") != discovered:
        raise ValidationError(f"{label} passed-test count does not match discovery.")

    for key in ("failed", "skipped", "flaky", "unexecuted", "nonstandard_expected"):
        if summary.get(key) != 0:
            raise ValidationError(f"{label} has nonzero {key} count.")

    return summary


def run_self_tests():
    """Run basic checks for shared validation behavior."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="forge-validation-") as temporary:
        base = Path(temporary)
        candidate_dir = base / "candidate"
        candidate_dir.mkdir()

        archive_name = "FORGE-Deployment-test.zip"
        archive = candidate_dir / archive_name
        archive.write_bytes(b"synthetic candidate archive")

        digest = sha256_file(archive)

        (candidate_dir / "manifest.json").write_text(
            json.dumps({
                "candidate_id": "test-candidate",
                "archive": archive_name,
                "sha256": digest,
            }),
            encoding="utf-8",
        )

        (candidate_dir / "SHA256SUMS").write_text(
            f"{digest}  {archive_name}\n",
            encoding="utf-8",
        )

        result = validate_candidate_artifacts(candidate_dir, "test-candidate")
        assert result["sha256"] == digest
        print("PASS: candidate archive and checksum validation")

        try:
            validate_candidate_artifacts(
                candidate_dir, "test-candidate", expected_sha="0" * 64
            )
        except ValidationError:
            print("PASS: candidate checksum mismatch rejected")
        else:
            raise AssertionError("Incorrect expected SHA-256 was accepted.")

    good_pytest = {
        "status": "PASSED",
        "discovered": 1,
        "passed": 1,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "flaky": 0,
        "unexecuted": 0,
        "duration_seconds": 0.1,
        "warning_count": 0,
        "warning_details": [],
        "tests": [{
            "classname": "test_example",
            "name": "test_pass",
            "status": "PASSED",
        }],
    }

    validate_pytest_summary(good_pytest)
    print("PASS: valid backend Pytest summary")

    bad_pytest = dict(good_pytest, passed=0)
    try:
        validate_pytest_summary(bad_pytest)
    except ValidationError:
        print("PASS: invalid backend Pytest summary rejected")
    else:
        raise AssertionError("Invalid Pytest summary was accepted.")

    good_e2e = {
        "eligible": True,
        "discovered": 1,
        "passed": 1,
        "failed": 0,
        "skipped": 0,
        "flaky": 0,
        "unexecuted": 0,
        "nonstandard_expected": 0,
    }

    validate_e2e_summary(good_e2e)
    print("PASS: valid E2E summary")

    bad_e2e = dict(good_e2e, eligible=False)
    try:
        validate_e2e_summary(bad_e2e)
    except ValidationError:
        print("PASS: ineligible E2E summary rejected")
    else:
        raise AssertionError("Ineligible E2E summary was accepted.")

    print("All shared validation self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_self_tests())
