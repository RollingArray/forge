#!/usr/bin/env python3
"""
FORGE Deployment Archive Validator

Author:
-------
Ranjoy Sen

Purpose:
--------
Verifies deployment archive contents and security requirements.

Responsibilities:
-----------------
- Check required deployment configuration files.
- Reject packaged JWT signing secrets and SMTP credentials.
- Validate sanitized deployment configuration.
"""


import json
import sys
import zipfile


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        auth_path = "forge-deployment/backend/api/config/authentication.json"
        email_path = "forge-deployment/backend/api/config/email.json"

        try:
            auth = json.loads(archive.read(auth_path))
            email = json.loads(archive.read(email_path))
        except KeyError as exc:
            raise SystemExit(f"ERROR: Required configuration missing from ZIP: {exc}")

        token = auth.get("development_token", {})
        if "secret" in token:
            raise SystemExit("ERROR: JWT signing secret detected in deployment ZIP.")

        smtp = email.get("smtp", {})
        sensitive_keys = {"password", "passwd", "secret", "api_key"}
        if any(key.lower() in sensitive_keys for key in smtp):
            raise SystemExit("ERROR: SMTP credential field detected in deployment ZIP.")

        if smtp.get("username") != "":
            raise SystemExit("ERROR: SMTP username was not sanitized.")
        if smtp.get("host") != "REPLACE_WITH_APPROVED_SMTP_HOST":
            raise SystemExit("ERROR: SMTP host was not sanitized.")
        if smtp.get("sender") != "REPLACE_WITH_APPROVED_SENDER":
            raise SystemExit("ERROR: SMTP sender was not sanitized.")

    print("Archive authentication secret check: PASS")
    print("Archive SMTP sanitization check: PASS")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: packaging.py ARCHIVE_PATH")
    verify_archive(sys.argv[1])
