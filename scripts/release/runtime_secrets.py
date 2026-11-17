#!/usr/bin/env python3
"""
FORGE Runtime Secret Manager

Author:
-------
Ranjoy Sen

Purpose:
--------
Creates secure secrets for isolated release runtimes.

Responsibilities:
-----------------
- Generate cryptographically secure JWT signing secrets.
- Write secrets with restricted file permissions.
"""


import secrets
import sys
from pathlib import Path


def write_jwt_secret(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(secrets.token_urlsafe(48) + "\n", encoding="utf-8")
    path.chmod(0o600)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: runtime_secrets.py SECRET_PATH")
    write_jwt_secret(sys.argv[1])
