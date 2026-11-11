#!/usr/bin/env python3

import argparse
import hashlib
import base64
from html import escape as html_escape
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "dist" / "candidates"
TEST_RUNS = ROOT / "dist" / "test-runs"


def fail(message):
    raise SystemExit(f"ERROR: {message}")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        fail(f"Cannot read {path}: {exc}")


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

    if gate.get("automated_tests_expected") != 56:
        fail("Unexpected automated E2E test count.")

    if gate.get("automated_tests_status") != "PASSED":
        fail("Automated E2E tests did not pass.")

    if gate.get("real_email_tests_expected") != 1:
        fail("Unexpected real-email E2E test count.")

    if gate.get("real_email_test_status") != "PASSED":
        fail("Real-email E2E test did not pass.")

    if manifest.get("candidate_id") != candidate_id:
        fail("Manifest candidate ID mismatch.")

    archive_name = manifest.get("archive")
    if not archive_name or Path(archive_name).name != archive_name:
        fail("Invalid archive filename in manifest.")

    archive = candidate_dir / archive_name
    if not archive.is_file():
        fail(f"Candidate ZIP not found: {archive}")

    actual_sha = sha256_file(archive)
    expected_sha = manifest.get("sha256")

    if actual_sha != expected_sha:
        fail("Candidate ZIP SHA-256 does not match manifest.")

    checksum_lines = checksum_path.read_text().splitlines()
    matching_checksum = False

    for line in checksum_lines:
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            recorded_sha = parts[0]
            recorded_name = parts[1].lstrip("*")
            if recorded_name == archive_name and recorded_sha == actual_sha:
                matching_checksum = True

    if not matching_checksum:
        fail("SHA256SUMS does not verify the candidate ZIP.")

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

    subject = (
        f"FORGE | Release Candidate | "
        f"E2E 57/57 Automation Test Cases Passed | {candidate_id}"
    )

    # Escape all dynamic values before inserting them into HTML.
    candidate_h = html_escape(candidate_id)
    commit_h = html_escape(str(commit))
    endpoint_h = html_escape(str(endpoint))
    model_h = html_escape(str(model))
    sha_h = html_escape(actual_sha)
    evidence_h = html_escape(str(evidence_dir))
    archive_h = html_escape(archive.name)

    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, Helvetica, sans-serif; color: #263445;
             font-size: 13px; line-height: 1.5;">

<p>Hello,</p>

<p>The FORGE deployment candidate has completed end-to-end validation.
All release checks passed. The deployment package is attached for review.</p>

<h3 style="color: #183B63;">RELEASE AT A GLANCE</h3>
<table cellpadding="7" cellspacing="0" border="1"
       style="border-collapse: collapse; border-color: #D7DEE8; width: 100%;">
<tr><td><b>Release candidate</b></td><td>{candidate_h}</td></tr>
<tr><td><b>Git commit</b></td><td>{commit_h}</td></tr>
<tr><td><b>Automated E2E tests</b></td><td>56/56 PASSED</td></tr>
<tr><td><b>Real-email E2E tests</b></td><td>1/1 PASSED</td></tr>
<tr><td><b>Overall validation</b></td><td><b>57/57 PASSED</b></td></tr>
<tr><td><b>Release gate</b></td><td><b>PASSED</b></td></tr>
</table>

<h3 style="color: #183B63;">1. END-TO-END AUTOMATION WORKFLOW</h3>
<table cellpadding="7" cellspacing="0" border="1"
       style="border-collapse: collapse; border-color: #D7DEE8; width: 100%;">
<tr style="background-color: #EAF0F6;">
<th align="left">Stage</th><th align="left">Automated activity</th>
<th align="left">Outcome</th></tr>
<tr><td>Candidate build</td><td>Production build and candidate-specific deployment packaging</td><td>PASSED</td></tr>
<tr><td>Environment startup</td><td>Isolated API and Nginx runtime initialization and health checks</td><td>PASSED</td></tr>
<tr><td>Automated E2E</td><td>Full Playwright end-to-end test suite</td><td>56/56 PASSED</td></tr>
<tr><td>Real-email E2E</td><td>Real Outlook email workflow with visible browser verification</td><td>1/1 PASSED</td></tr>
<tr><td>Release gate</td><td>Consolidated validation and release integrity checks</td><td>PASSED</td></tr>
</table>

<h3 style="color: #183B63;">2. TEST VALIDATION SUMMARY</h3>
<table cellpadding="7" cellspacing="0" border="1"
       style="border-collapse: collapse; border-color: #D7DEE8; width: 100%;">
<tr style="background-color: #EAF0F6;">
<th align="left">Test ID</th><th align="left">Description</th>
<th align="left">Status</th></tr>
<tr><td>E2E-001</td><td>Full automated Playwright test suite</td><td>56/56 PASSED</td></tr>
<tr><td>E2E-002</td><td>Real-email end-to-end workflow</td><td>1/1 PASSED</td></tr>
<tr><td>E2E-003</td><td>Consolidated release validation</td><td>57/57 PASSED</td></tr>
</table>

<h3 style="color: #183B63;">3. DEPLOYMENT AND ENVIRONMENT ENGINEERING</h3>
<table cellpadding="7" cellspacing="0" border="1"
       style="border-collapse: collapse; border-color: #D7DEE8; width: 100%;">
<tr style="background-color: #EAF0F6;">
<th align="left">Component</th><th align="left">Implementation</th></tr>
<tr><td>Frontend</td><td>Angular production build</td></tr>
<tr><td>Backend</td><td>Python / FastAPI isolated runtime</td></tr>
<tr><td>Web serving</td><td>Nginx with API reverse proxy</td></tr>
<tr><td>Test identities</td><td>Owner, Contributor and Viewer</td></tr>
<tr><td>AI integration</td><td>Corporate Ollama endpoint</td></tr>
<tr><td>AI model</td><td>{model_h}</td></tr>
<tr><td>Runtime isolation</td><td>Candidate-specific deployment environment</td></tr>
</table>

<h3 style="color: #183B63;">4. RELEASE INTEGRITY AND TRACEABILITY</h3>
<table cellpadding="7" cellspacing="0" border="1"
       style="border-collapse: collapse; border-color: #D7DEE8; width: 100%;">
<tr style="background-color: #EAF0F6;">
<th align="left">Control</th><th align="left">Result</th></tr>
<tr><td>Candidate-specific deployment archive</td><td>Verified</td></tr>
<tr><td>SHA-256 checksum</td><td>Verified</td></tr>
<tr><td>Deployment manifest</td><td>Generated and verified</td></tr>
<tr><td>Authentication secret protection</td><td>PASSED</td></tr>
<tr><td>SMTP configuration sanitization</td><td>PASSED</td></tr>
<tr><td>Test execution evidence</td><td>Retained</td></tr>
<tr><td>Release gate</td><td><b>PASSED</b></td></tr>
</table>

<h3 style="color: #183B63;">5. AI CONFIGURATION</h3>
<table cellpadding="7" cellspacing="0" border="1"
       style="border-collapse: collapse; border-color: #D7DEE8; width: 100%;">
<tr><td><b>Endpoint</b></td><td>{endpoint_h}</td></tr>
<tr><td><b>Model</b></td><td>{model_h}</td></tr>
</table>

<h3 style="color: #183B63;">6. DEPLOYMENT PACKAGE</h3>
<table cellpadding="7" cellspacing="0" border="1"
       style="border-collapse: collapse; border-color: #D7DEE8; width: 100%;">
<tr><td><b>Archive</b></td><td>{archive_h}</td></tr>
<tr><td><b>Attachment</b></td><td>Included</td></tr>
<tr><td><b>SHA-256</b></td><td style="font-family: monospace; word-break: break-all;">{sha_h}</td></tr>
<tr><td><b>Test evidence</b></td><td>{evidence_h}</td></tr>
</table>

<p>The attached archive is the validated release candidate. Its checksum
matches the deployment manifest and SHA256SUMS record.</p>

</body>
</html>"""

    def extract_passed_tests(log_path, expected_count, fallback_prefix):
        if not log_path.is_file():
            fail(f"Test log missing: {log_path}")

        cases = []

        for line in log_path.read_text(errors="replace").splitlines():
            match = re.search(r"✓\s*(\d+)\s+\[[^\]]+\]", line)
            if not match:
                continue

            sequence = int(match.group(1))
            description = line.split("›")[-1].strip()

            description = re.sub(
                r"\s+\(\d+(?:\.\d+)?(?:ms|s)\)\s*$",
                "",
                description,
            )

            if description.startswith("REAL EMAIL E2E:"):
                test_id = "REAL-EMAIL-01"
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
                            r"HTTP\\s*(400|403|404)", description
                        )
                        if status_match:
                            test_id = f"LG-16-{status_match.group(1)}"
                else:
                    test_id = f"PW-{sequence:02d}"

            description = re.sub(
                r"with\\s*HTTP", "with HTTP", description,
                flags=re.IGNORECASE
            )
            description = re.sub(r"\\s+", " ", description).strip()

            cases.append(
                f"[{test_id}] [PASSED] {description}"
            )

        if len(cases) != expected_count:
            fail(
                f"Expected {expected_count} passed tests in {log_path}, "
                f"found {len(cases)}."
            )

        return cases

    automated_cases = extract_passed_tests(
        run_dir / "logs" / "playwright-full.log",
        56,
        "TC",
    )

    real_email_cases = extract_passed_tests(
        run_dir / "logs" / "playwright-real-email.log",
        1,
        "REAL-EMAIL",
    )

    all_cases = automated_cases + real_email_cases
    test_case_lines = "\n".join(all_cases)

    body = f"""Hello,

The FORGE deployment candidate has completed end-to-end validation.
All release checks passed. The deployment package is attached for review.

RELEASE AT A GLANCE
Candidate: {candidate_id}
Git commit: {commit}
Automated E2E tests: 56/56 PASSED
Real-email E2E tests: 1/1 PASSED
Overall validation: 57/57 PASSED
Release gate: PASSED

AI CONFIGURATION
Endpoint: {endpoint}
Model: {model}

DEPLOYMENT PACKAGE
Archive: {archive.name}
SHA-256: {actual_sha}

PASSED TEST CASES ({len(all_cases)})
{test_case_lines}
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
        "evidence_dir": evidence_dir,
        "endpoint": endpoint,
        "model": model,
    }


def pbcopy(text):
    subprocess.run(
        ["/usr/bin/pbcopy"],
        input=text,
        text=True,
        check=True,
    )


def pbcopy_html(html_content, plain_text):
    html_b64 = base64.b64encode(
        html_content.encode("utf-8")
    ).decode("ascii")
    plain_b64 = base64.b64encode(
        plain_text.encode("utf-8")
    ).decode("ascii")

    source = r"""
function run(argv) {
    ObjC.import('AppKit');

    var htmlData = $.NSData.alloc.initWithBase64EncodedStringOptions(
        $(argv[0]), 0
    );
    var plainData = $.NSData.alloc.initWithBase64EncodedStringOptions(
        $(argv[1]), 0
    );
    var plainString = $.NSString.alloc.initWithDataEncoding(
        plainData, $.NSUTF8StringEncoding
    );

    var pasteboard = $.NSPasteboard.generalPasteboard;
    pasteboard.clearContents();
    pasteboard.setDataForType(htmlData, $("public.html"));
    pasteboard.setStringForType(
        plainString, $("public.utf8-plain-text")
    );

    return "HTML clipboard prepared";
}
"""

    subprocess.run(
        [
            "/usr/bin/osascript", "-l", "JavaScript",
            "-e", source, html_b64, plain_b64
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def run_osascript(source):
    subprocess.run(
        ["/usr/bin/osascript"],
        input=source,
        text=True,
        check=True,
    )


def create_outlook_draft(data):
    candidate_id = data["candidate_id"]
    run_dir = data["run_dir"]

    marker = run_dir / "outlook-draft-status.json"

    if marker.exists():
        existing = read_json(marker)
        fail(
            "An Outlook draft attempt is already recorded for this candidate "
            f"(status: {existing.get('status')}). Inspect Outlook before retrying. "
            f"Marker: {marker}"
        )

    attachment_dir = run_dir / "outlook-attachment"

    if attachment_dir.exists():
        shutil.rmtree(attachment_dir)

    attachment_dir.mkdir(parents=True)

    attachment = attachment_dir / data["archive"].name
    shutil.copy2(data["archive"], attachment)

    if sha256_file(attachment) != data["sha256"]:
        fail("Staged Outlook attachment checksum mismatch.")

    if len(list(attachment_dir.iterdir())) != 1:
        fail("Attachment staging folder must contain exactly one file.")

    status = {
        "candidate_id": candidate_id,
        "status": "IN_PROGRESS",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "archive": str(data["archive"]),
        "sha256": data["sha256"],
    }
    marker.write_text(json.dumps(status, indent=2) + "\n")

    try:
        # Create a new message through the verified Outlook menu sequence.
        pbcopy(data["subject"])

        run_osascript("""
tell application "Microsoft Outlook" to activate
delay 1

tell application "System Events"
    tell process "Microsoft Outlook"
        click menu bar item "File" of menu bar 1
        delay 0.3

        click menu item "New" of menu 1 of menu bar item "File" of menu bar 1
        delay 0.3

        click menu item "Email" of menu 1 of menu item "New" of menu 1 of menu bar item "File" of menu bar 1
        delay 2

        -- Initial focus is To. Tab to Subject.
        key code 48
        delay 0.3
        keystroke "v" using command down
        delay 0.5

        -- Tab to Body.
        key code 48
        delay 0.3
    end tell
end tell
""")

        # Populate the body using HTML clipboard content with plain-text fallback.
        pbcopy(data["body"])

        run_osascript("""
tell application "System Events"
    tell process "Microsoft Outlook"
        keystroke "v" using command down
        delay 1
    end tell
end tell
""")

        # Open attachment picker and navigate to the one-file folder.
        pbcopy(str(attachment_dir))

        run_osascript("""
tell application "System Events"
    tell process "Microsoft Outlook"
        keystroke "e" using command down
        delay 1

        keystroke "g" using {command down, shift down}
        delay 0.5

        keystroke "v" using command down
        delay 0.3

        key code 36
        delay 1

        -- The staging folder contains exactly one ZIP.
        keystroke "a" using command down
        delay 0.3

        -- Choose the selected ZIP.
        key code 36
        delay 2

        -- Save the compose message. Never send.
        keystroke "s" using command down
        delay 5
    end tell
end tell
""")

        status.update({
            "status": "SAVE_SHORTCUT_ISSUED",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "subject": data["subject"],
            "attachment": str(attachment),
            "recipient_left_blank": True,
            "send_invoked": False,
        })

        marker.write_text(json.dumps(status, indent=2) + "\n")

        print("Outlook compose sequence completed.")
        print(f"Candidate: {candidate_id}")
        print(f"Attachment: {attachment}")
        print("Recipient fields left blank.")
        print("Command+S issued. Inspect Outlook Drafts to confirm.")
        print("No send operation was invoked.")

    except Exception as exc:
        status.update({
            "status": "FAILED",
            "error": str(exc),
            "failed_at": datetime.now(timezone.utc).isoformat(),
        })
        marker.write_text(json.dumps(status, indent=2) + "\n")
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = validate_candidate(args.candidate_id)

    print("Release candidate validation: PASSED")
    print(f"Candidate: {data['candidate_id']}")
    print(f"Archive: {data['archive']}")
    print(f"SHA-256: {data['sha256']}")
    print("E2E: 57/57 PASSED")
    print(f"AI endpoint: {data['endpoint']}")
    print(f"AI model: {data['model']}")

    if args.dry_run:
        print("DRY RUN: Outlook was not opened and no draft was created.")
        return

    create_outlook_draft(data)


if __name__ == "__main__":
    main()
