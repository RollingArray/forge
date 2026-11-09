#!/usr/bin/env python3
"""Build an isolated FORGE E2E deployment from current source."""

from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "forge-e2e"
STAGE = OUTPUT / "forge-deployment"
ZIP_PATH = OUTPUT / "forge-e2e-deployment.zip"
BOOTSTRAP_PATH = OUTPUT / "e2e-bootstrap.key"

FRONTEND = ROOT / "frontend" / "dist" / "forge-ui" / "browser"
BACKEND = ROOT / "backend" / "api"
SOURCE_APP = BACKEND / "app"
E2E_AUTH_SOURCE = ROOT / "scripts" / "e2e" / "e2e_auth.py"

REQUIRED = [
    ROOT / "pyproject.toml",
    ROOT / "uv.lock",
    ROOT / ".python-version",
    FRONTEND / "index.html",
    SOURCE_APP / "main.py",
    BACKEND / "config" / "ai.json",
    BACKEND / "config" / "email.json",
    BACKEND / "config" / "authentication.json",
    E2E_AUTH_SOURCE,
]

def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")

def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main() -> None:
    if OUTPUT.exists():
        fail(
            f"{OUTPUT} already exists. Nothing was deleted or overwritten. "
            "Inspect it before deciding how to proceed."
        )

    for path in REQUIRED:
        if not path.exists():
            fail(f"Required build input is missing: {path.relative_to(ROOT)}")

    python_version = (ROOT / ".python-version").read_text(
        encoding="utf-8"
    ).strip()
    if python_version != "3.11":
        fail(f"Expected Python 3.11, found {python_version!r}")

    if (SOURCE_APP / "api" / "e2e_auth.py").exists():
        fail("E2E router already exists in source backend. Refusing to continue.")

    main_source = (SOURCE_APP / "main.py").read_text(encoding="utf-8")
    if "app.include_router(" not in main_source:
        fail("Could not locate router registration in source main.py.")
    if "e2e_auth" in main_source:
        fail("Source main.py already mentions E2E authentication.")

    OUTPUT.mkdir(parents=True)
    (STAGE / "backend" / "api").mkdir(parents=True)
    (STAGE / "frontend").mkdir(parents=True)
    (STAGE / "backend" / "api" / "config").mkdir(parents=True)
    (STAGE / "backend" / "api" / "data").mkdir(parents=True)

    # Locked project metadata belongs at the deployment root.
    for name in ("pyproject.toml", "uv.lock", ".python-version"):
        shutil.copy2(ROOT / name, STAGE / name)

    # Copy the current application and compiled Angular browser output.
    shutil.copytree(SOURCE_APP, STAGE / "backend" / "api" / "app")
    shutil.copytree(FRONTEND, STAGE / "frontend", dirs_exist_ok=True)

    # Add the E2E-only endpoint to the extracted copy, never source.
    staged_app = STAGE / "backend" / "api" / "app"
    shutil.copy2(
        E2E_AUTH_SOURCE,
        staged_app / "api" / "e2e_auth.py",
    )

    staged_main = staged_app / "main.py"
    staged_text = staged_main.read_text(encoding="utf-8")
    import_anchor = "from app.api.auth import router as authentication_router"
    if staged_text.count(import_anchor) != 1:
        fail("Unexpected main.py import layout; router was not registered.")

    staged_text = staged_text.replace(
        import_anchor,
        import_anchor + "\n"
        "from app.api.e2e_auth import router as e2e_auth_router",
        1,
    )

    registration_anchor = (
        "app.include_router(\n"
        "    authentication_router,\n"
        '    prefix="/api/v1",\n'
        ")"
    )
    if staged_text.count(registration_anchor) != 1:
        fail("Unexpected authentication router registration layout.")

    staged_text = staged_text.replace(
        registration_anchor,
        registration_anchor + "\n\n"
        "app.include_router(\n"
        "    e2e_auth_router,\n"
        '    prefix="/api/v1/__e2e/auth",\n'
        ")",
        1,
    )
    staged_main.write_text(staged_text, encoding="utf-8")

    # E2E configuration: independent JWT secret and no corporate SMTP.
    source_config = BACKEND / "config"
    source_auth = json.loads(
        (source_config / "authentication.json").read_text(encoding="utf-8")
    )
    source_token = source_auth.get("development_token", {})

    auth_config = {
        "allowed_domains": ["collins.com"],
        "development_token": {
            "algorithm": source_token.get("algorithm", "HS256"),
            "expiration_minutes": 720,
            "secret": secrets.token_urlsafe(48),
        },
    }

    ai_config = json.loads(
        (source_config / "ai.json").read_text(encoding="utf-8")
    )
    # Prevent accidental calls to the developer's local Ollama instance.
    ai_config["base_url"] = "http://127.0.0.1:9"
    ai_config["capability_timeout_seconds"] = 0.5
    ai_config["generation_timeout_seconds"] = 2.0

    email_config = json.loads(
        (source_config / "email.json").read_text(encoding="utf-8")
    )
    email_config.setdefault("magic_link", {})[
        "frontend_base_url"
    ] = "http://127.0.0.1:18866"

    config_dir = STAGE / "backend" / "api" / "config"
    write_json(config_dir / "authentication.json", auth_config)
    write_json(config_dir / "ai.json", ai_config)
    write_json(config_dir / "email.json", email_config)

    # Start with empty E2E-only runtime data.
    data_dir = STAGE / "backend" / "api" / "data"
    (data_dir / ".gitkeep").write_text("", encoding="utf-8")

    bootstrap_key = secrets.token_urlsafe(48)
    BOOTSTRAP_PATH.write_text(bootstrap_key + "\n", encoding="utf-8")
    BOOTSTRAP_PATH.chmod(0o600)

    (STAGE / "README-E2E.md").write_text(
        "# FORGE isolated E2E deployment\n\n"
        "Built from current source and current compiled frontend.\n"
        "This package contains an E2E-only session bootstrap endpoint.\n"
        "It must only be bound to loopback and used for controlled tests.\n"
        "The bootstrap key is stored separately in the parent E2E directory.\n"
        "No corporate SMTP credentials or runtime user data are included.\n",
        encoding="utf-8",
    )

    # Zip only the deployment tree. Never include the bootstrap key.
    with zipfile.ZipFile(
        ZIP_PATH,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(OUTPUT),
                )

    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
        if any("e2e-bootstrap.key" in name for name in names):
            fail("Bootstrap key was unexpectedly included in deployment ZIP.")
        if not any(name.endswith("app/api/e2e_auth.py") for name in names):
            fail("E2E authentication endpoint missing from ZIP.")
        if not any(name.endswith("frontend/index.html") for name in names):
            fail("Compiled frontend missing from ZIP.")

    print("E2E DEPLOYMENT BUILD COMPLETE")
    print(f"Deployment directory: {STAGE}")
    print(f"Deployment ZIP:       {ZIP_PATH}")
    print(f"Bootstrap key:        {BOOTSTRAP_PATH}")
    print(f"ZIP size:             {ZIP_PATH.stat().st_size:,} bytes")
    print(f"Frontend index SHA:   {sha256(STAGE / 'frontend' / 'index.html')}")
    print("Source backend modified: NO")
    print("Existing deployment modified: NO")
    print("SMTP credentials packaged: NO")
    print("Bootstrap key packaged in ZIP: NO")

if __name__ == "__main__":
    main()
