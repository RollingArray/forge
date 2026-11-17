"""
FORGE Release Draft Orchestrator

Author:
-------
Ranjoy Sen

Purpose:
--------
Provides the command-line entry point for release draft preparation.

Responsibilities:
-----------------
- Validate the selected release candidate.
- Summarize backend and E2E validation results.
- Support dry-run and Outlook draft preparation modes.
"""


import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from release.outlook import create_outlook_draft
from release.release_content import validate_candidate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume-existing-compose", action="store_true")
    args = parser.parse_args()

    data = validate_candidate(args.candidate_id)

    print("Release candidate validation: PASSED")
    print(f"Candidate: {data['candidate_id']}")
    print(f"Archive: {data['archive']}")
    print(f"SHA-256: {data['sha256']}")
    automated_count = data["automated_count"]
    real_email_count = data["real_email_count"]
    total_count = data["total_count"]
    print(f"Backend Pytest: {data['backend_count']}/{data['backend_count']} PASSED")
    print(f"Automated E2E: {automated_count}/{automated_count} PASSED")
    print(f"Real-email E2E: {real_email_count}/{real_email_count} PASSED")
    print(f"Overall validation: {total_count}/{total_count} PASSED")
    print(f"AI endpoint: {data['endpoint']}")
    print(f"AI model: {data['model']}")

    if args.dry_run:
        print("DRY RUN: Outlook was not opened and no draft was created.")
        return

    create_outlook_draft(data, resume_existing_compose=args.resume_existing_compose)


if __name__ == "__main__":
    raise SystemExit(main())
