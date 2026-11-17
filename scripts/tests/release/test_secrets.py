"""
FORGE Runtime Secret Tests

Author:
-------
Ranjoy Sen

Purpose:
--------
Verifies secure generation and storage of runtime JWT secrets.

Responsibilities:
-----------------
- Test JWT secret file creation.
- Verify minimum secret length.
- Verify restrictive file permissions.
"""


from scripts.release.runtime_secrets import write_jwt_secret


def test_write_jwt_secret_creates_private_file(tmp_path):
    secret_file = tmp_path / "secrets" / "jwt.secret"

    write_jwt_secret(secret_file)

    assert secret_file.is_file()
    assert len(secret_file.read_text().strip()) >= 32
    assert secret_file.stat().st_mode & 0o777 == 0o600
