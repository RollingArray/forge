"""
FORGE Deployment Archive Tests

Author:
-------
Ranjoy Sen

Purpose:
--------
Verifies deployment archive contents and security requirements.

Responsibilities:
-----------------
- Test required configuration files in deployment archives.
- Verify JWT signing secrets are not packaged.
- Verify SMTP credentials are not packaged.
- Test rejection of invalid or unsafe archive contents.
"""

import json
import zipfile

import pytest

from scripts.release.packaging import verify_archive


def make_archive(path, auth, email):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "forge-deployment/backend/api/config/authentication.json",
            json.dumps(auth),
        )
        archive.writestr(
            "forge-deployment/backend/api/config/email.json",
            json.dumps(email),
        )


def valid_auth():
    return {"development_token": {"algorithm": "HS256"}}


def valid_email():
    return {
        "smtp": {
            "host": "mailhub.utc.com",
            "port": 25,
            "username": "",
            "sender": "forge@collins.com",
            "display_name": "FORGE",
            "use_starttls": False,
            "timeout_seconds": 15,
        },
        "magic_link": {
            "expiration_minutes": 5,
            "frontend_base_url": "https://forge.ai.in.collins.com/",
        },
    }


def test_verify_archive_accepts_sanitized_configuration(tmp_path, capsys):
    archive = tmp_path / "deployment.zip"
    make_archive(archive, valid_auth(), valid_email())

    verify_archive(archive)

    output = capsys.readouterr().out
    assert "authentication secret check: PASS" in output
    assert "SMTP sanitization check: PASS" in output


def test_verify_archive_rejects_jwt_secret(tmp_path):
    archive = tmp_path / "deployment.zip"
    make_archive(
        archive,
        {"development_token": {"secret": "unsafe"}},
        valid_email(),
    )

    with pytest.raises(SystemExit, match="JWT signing secret"):
        verify_archive(archive)


def test_verify_archive_rejects_smtp_password(tmp_path):
    archive = tmp_path / "deployment.zip"
    email = valid_email()
    email["smtp"]["password"] = "unsafe"
    make_archive(archive, valid_auth(), email)

    with pytest.raises(SystemExit, match="SMTP credential"):
        verify_archive(archive)


def test_verify_archive_rejects_unsanitized_username(tmp_path):
    archive = tmp_path / "deployment.zip"
    email = valid_email()
    email["smtp"]["username"] = "local-user"
    make_archive(archive, valid_auth(), email)

    with pytest.raises(SystemExit, match="username"):
        verify_archive(archive)


def test_verify_archive_rejects_missing_config(tmp_path):
    archive = tmp_path / "deployment.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("unrelated.txt", "content")

    with pytest.raises(SystemExit, match="Required configuration"):
        verify_archive(archive)



def test_verify_archive_rejects_wrong_smtp_configuration(tmp_path):
    archive = tmp_path / "deployment.zip"
    email = valid_email()
    email["smtp"]["port"] = 587
    make_archive(archive, valid_auth(), email)

    with pytest.raises(SystemExit, match="SMTP configuration mismatch"):
        verify_archive(archive)


def test_verify_archive_rejects_wrong_frontend_url(tmp_path):
    archive = tmp_path / "deployment.zip"
    email = valid_email()
    email["magic_link"]["frontend_base_url"] = "http://localhost:4200"
    make_archive(archive, valid_auth(), email)

    with pytest.raises(SystemExit, match="frontend URL"):
        verify_archive(archive)
