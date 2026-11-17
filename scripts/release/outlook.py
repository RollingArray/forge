"""
FORGE Outlook Release Draft Manager

Author:
-------
Ranjoy Sen

Purpose:
--------
Prepares Outlook release drafts and handles supporting attachments.

Responsibilities:
-----------------
- Prepare release email content and attachments.
- Validate release information before draft preparation.
- Support Outlook compose and clipboard interactions.
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


from release.release_content import fail, read_json, sha256_file

def pbcopy(text):
    subprocess.run(
        ["/usr/bin/pbcopy"],
        input=text,
        text=True,
        check=True,
    )
def pbcopy_html(html_content, plain_text):
    # Use the reliable macOS clipboard path.
    # Outlook receives the complete email body as plain text.
    pbcopy(plain_text)
def run_osascript(source):
    subprocess.run(
        ["/usr/bin/osascript"],
        input=source,
        text=True,
        check=True,
    )
def create_outlook_draft(data, resume_existing_compose=False):
    candidate_id = data["candidate_id"]
    run_dir = data["run_dir"]

    marker = run_dir / "outlook-draft-status.json"

    existing = read_json(marker) if marker.exists() else None

    if existing and not resume_existing_compose:
        fail(
            "An Outlook draft attempt is already recorded for this candidate "
            f"(status: {existing.get('status')}). Use --resume-existing-compose "
            "only when the original compose window is still open."
        )

    if resume_existing_compose:
        if not existing or existing.get("status") != "FAILED":
            fail("Resume requires an existing FAILED Outlook status marker.")
        if existing.get("candidate_id") != candidate_id:
            fail("The failed Outlook marker belongs to a different candidate.")

    attachment_dir = run_dir / "outlook-attachment"

    sources = [
        data["archive"],
        data["e2e_report"],
        data["pytest_report"],
    ]

    staged_attachments = []

    if resume_existing_compose:
        if not attachment_dir.is_dir():
            fail("Existing Outlook attachment staging directory is missing.")

        existing_files = {
            item.name for item in attachment_dir.iterdir() if item.is_file()
        }
        expected_files = {item.name for item in sources}

        if existing_files != expected_files:
            fail("Existing Outlook staging folder does not contain exactly the three expected files.")

        for source_path in sources:
            staged_path = attachment_dir / source_path.name

            if not source_path.is_file() or not staged_path.is_file():
                fail(f"Required Outlook attachment is missing: {source_path.name}")

            source_sha = sha256_file(source_path)
            staged_sha = sha256_file(staged_path)

            if source_sha != staged_sha:
                fail(f"Existing staged attachment checksum mismatch: {source_path.name}")

            if source_path == data["archive"] and staged_sha != data["sha256"]:
                fail("Staged deployment ZIP does not match the validated candidate checksum.")

            staged_attachments.append({
                "name": staged_path.name,
                "path": str(staged_path),
                "size_bytes": staged_path.stat().st_size,
                "sha256": staged_sha,
            })
    else:
        if attachment_dir.exists():
            shutil.rmtree(attachment_dir)

        attachment_dir.mkdir(parents=True)

        for source_path in sources:
            if not source_path.is_file() or source_path.stat().st_size == 0:
                fail(f"Required Outlook attachment is missing or empty: {source_path}")

            staged_path = attachment_dir / source_path.name
            shutil.copy2(source_path, staged_path)

            source_sha = sha256_file(source_path)
            staged_sha = sha256_file(staged_path)

            if source_sha != staged_sha:
                fail(f"Staged attachment checksum mismatch: {source_path.name}")

            if source_path == data["archive"] and staged_sha != data["sha256"]:
                fail("Staged deployment ZIP does not match the validated candidate checksum.")

            staged_attachments.append({
                "name": staged_path.name,
                "path": str(staged_path),
                "size_bytes": staged_path.stat().st_size,
                "sha256": staged_sha,
            })

    if len(staged_attachments) != 3:
        fail("Outlook staging must contain exactly three attachments.")

    if len(list(attachment_dir.iterdir())) != 3:
        fail("Attachment staging folder must contain exactly three files.")


    status = {
        "candidate_id": candidate_id,
        "status": "RESUME_IN_PROGRESS" if resume_existing_compose else "IN_PROGRESS",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "archive": str(data["archive"]),
        "sha256": data["sha256"],
        "attachments": staged_attachments,
        "resumed_existing_compose": resume_existing_compose,
    }
    marker.write_text(json.dumps(status, indent=2) + "\n")

    try:
        if resume_existing_compose:
            run_osascript("""
tell application "Microsoft Outlook" to activate
delay 1
""")
        else:
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

        pbcopy_html(data["html_body"], data["body"])

        run_osascript("""
tell application "System Events"
    tell process "Microsoft Outlook"
        keystroke "v" using command down
        delay 1
    end tell
end tell
""")

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

        -- Select the three verified attachments.
        keystroke "a" using command down
        delay 0.3

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
            "recipient_left_blank": True,
            "send_invoked": False,
        })

        marker.write_text(json.dumps(status, indent=2) + "\n")

        print("Outlook compose sequence completed.")
        print(f"Candidate: {candidate_id}")
        print("Attachments staged:")
        for item in staged_attachments:
            print(f"  {item['name']} ({item['size_bytes']} bytes)")
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
