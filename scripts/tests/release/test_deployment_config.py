from pathlib import Path
"""
FORGE Deployment Configuration Tests

Author:
-------
Ranjoy Sen

Purpose:
--------
Verifies deployment configuration validation and preparation.

Responsibilities:
-----------------
- Test corporate Ollama configuration validation.
- Test model availability configuration.
- Verify runtime email configuration handling.
- Verify sanitized deployment configuration staging.
"""


import json

import pytest

from scripts.release.deployment_config import (
    ollama_config,
    ollama_model,
    runtime_email,
    stage_config,
)


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_ollama_config_validates_and_prints_values(tmp_path, capsys):
    config = tmp_path / "ai.json"
    write_json(config, {
        "provider": "ollama",
        "base_url": "http://localhost:11434/",
        "model": "test-model",
    })

    ollama_config(config)

    assert capsys.readouterr().out.strip() == "http://localhost:11434\ttest-model"


def test_ollama_config_rejects_non_ollama_provider(tmp_path):
    config = tmp_path / "ai.json"
    write_json(config, {"provider": "openai"})

    with pytest.raises(SystemExit, match="provider is not Ollama"):
        ollama_config(config)


def test_ollama_model_checks_available_model(tmp_path, capsys):
    tags = tmp_path / "tags.json"
    write_json(tags, {"models": [{"name": "test-model"}]})

    ollama_model(tags, "test-model")

    assert "PASS:" in capsys.readouterr().out


def test_ollama_model_rejects_missing_model(tmp_path):
    tags = tmp_path / "tags.json"
    write_json(tags, {"models": [{"name": "other-model"}]})

    with pytest.raises(SystemExit):
        ollama_model(tags, "test-model")


def test_runtime_email_rejects_smtp_credentials(tmp_path):
    source = tmp_path / "email.json"
    write_json(source, {
        "smtp": {
            "host": "smtp.example.com",
            "port": 25,
            "sender": "forge@example.com",
            "password": "must-not-copy",
        }
    })

    with pytest.raises(SystemExit, match="credentials"):
        runtime_email(source, tmp_path / "runtime")


def test_stage_config_sanitizes_auth_and_smtp(tmp_path, monkeypatch):
    source = tmp_path / "source"
    stage = tmp_path / "stage"
    config = source / "backend/api/config"
    config.mkdir(parents=True)

    write_json(config / "ai.json", {
        "provider": "ollama",
        "base_url": "http://old-host",
        "model": "old-model",
    })
    write_json(config / "email.json", {
        "smtp": {
            "host": "local-host",
            "sender": "local@example.com",
            "username": "local-user",
            "password": "local-password",
        },
        "magic_link": {},
    })
    write_json(config / "authentication.json", {
        "allowed_domains": ["example.com"],
        "development_token": {
            "algorithm": "HS256",
            "expiration_minutes": 45,
            "secret": "must-not-copy",
        },
    })
    monkeypatch.setenv("FORGE_FRONTEND_BASE_URL", "https://forge.example.com")

    stage_config(source, stage, "http://approved-host:11434", "approved-model")

    staged = stage / "backend/api/config"
    ai = json.loads((staged / "ai.json").read_text())
    email = json.loads((staged / "email.json").read_text())
    auth = json.loads((staged / "authentication.json").read_text())

    assert ai["base_url"] == "http://approved-host:11434"
    assert ai["model"] == "approved-model"
    assert email["smtp"]["host"] == "REPLACE_WITH_APPROVED_SMTP_HOST"
    assert email["smtp"]["sender"] == "REPLACE_WITH_APPROVED_SENDER"
    assert email["smtp"]["username"] == ""
    assert "password" not in email["smtp"]
    assert email["magic_link"]["frontend_base_url"] == "https://forge.example.com"
    assert "secret" not in auth["development_token"]
    assert auth["allowed_domains"] == ["example.com"]


def test_stage_config_rejects_invalid_frontend_url(tmp_path, monkeypatch):
    source = tmp_path / "source"
    config = source / "backend/api/config"
    config.mkdir(parents=True)
    write_json(config / "ai.json", {})
    write_json(config / "email.json", {"smtp": {}, "magic_link": {}})
    write_json(config / "authentication.json", {})
    monkeypatch.setenv("FORGE_FRONTEND_BASE_URL", "not-a-url")

    with pytest.raises(SystemExit, match="HTTP"):
        stage_config(source, tmp_path / "stage", "http://host", "model")


def test_release_content_paths_resolve_from_repository_root(tmp_path):
    import os
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[3]

    code = """
from pathlib import Path
from release import release_content

repo_root = Path.cwd().resolve()

assert release_content.ROOT == repo_root
assert release_content.CANDIDATES == repo_root / "dist" / "candidates"
assert release_content.TEST_RUNS == repo_root / "dist" / "test-runs"

print("PASS: Release content paths resolve from repository root.")
"""

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "scripts")

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "PASS:" in result.stdout


def test_release_nginx_configs_allow_ai_generation_timeout():
    repo_root = Path(__file__).resolve().parents[3]

    candidate = (
        repo_root / "scripts/release/deployment_candidate.sh"
    ).read_text(encoding="utf-8")

    bundle = (
        repo_root / "scripts/release/deployment_bundle.sh"
    ).read_text(encoding="utf-8")

    assert (
        "proxy_pass http://127.0.0.1:18875;\n"
        "      proxy_read_timeout 210s;"
    ) in candidate

    assert (
        "proxy_pass http://127.0.0.1:8000;\n"
        "        proxy_http_version 1.1;\n"
        "        proxy_read_timeout 210s;"
    ) in bundle

    assert (
        "proxy_pass http://127.0.0.1:18765;\n"
        "      proxy_read_timeout 210s;"
    ) in bundle
