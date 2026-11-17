#!/usr/bin/env python3
"""
FORGE Deployment Configuration Manager

Author:
-------
Ranjoy Sen

Purpose:
--------
Validates and prepares configuration used by deployment builds and runtimes.

Responsibilities:
-----------------
- Validate corporate Ollama configuration and model availability.
- Prepare sanitized deployment configuration.
- Apply runtime email configuration safely.
"""


import argparse
import json
import os
import sys
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ollama_config(path):
    config = load_json(path)
    if config.get("provider") != "ollama":
        raise SystemExit("Candidate AI provider is not Ollama.")

    base_url = str(config.get("base_url", "")).strip().rstrip("/")
    model = str(config.get("model", "")).strip()
    if not base_url.startswith(("http://", "https://")) or not model:
        raise SystemExit("Candidate Ollama URL or model is missing.")

    print(f"{base_url}\t{model}")


def ollama_model(path, model):
    payload = load_json(path)
    models = payload.get("models", [])
    names = {
        str(item.get("name", ""))
        for item in models
        if isinstance(item, dict)
    }

    if model not in names:
        print("Available models:", ", ".join(sorted(names)) or "<none>", file=sys.stderr)
        raise SystemExit(1)

    print(f"PASS: Corporate Ollama model available: {model}")


def runtime_email(source_path, runtime_config):
    email_source = Path(source_path)
    runtime_config = Path(runtime_config)
    runtime_config.mkdir(parents=True, exist_ok=True)

    email = load_json(email_source)
    smtp = email.get("smtp", {})

    if not smtp.get("host") or not smtp.get("port") or not smtp.get("sender"):
        raise SystemExit("Local SMTP host, port and sender must be configured.")
    if smtp.get("username"):
        raise SystemExit("Unexpected SMTP username. Review local E2E SMTP configuration.")
    if any(k.lower() in {"password", "passwd", "secret", "api_key"} for k in smtp):
        raise SystemExit("SMTP credentials must not be copied into the E2E runtime.")

    email.setdefault("magic_link", {})["frontend_base_url"] = "http://127.0.0.1:18876"
    (runtime_config / "email.json").write_text(
        json.dumps(email, indent=2) + "\n",
        encoding="utf-8",
    )


def stage_config(source, stage, deploy_ai_base_url, deploy_ai_model):
    source = Path(source)
    stage = Path(stage)
    src_cfg = source / "backend/api/config"
    dst_cfg = stage / "backend/api/config"

    ai = load_json(src_cfg / "ai.json")
    ai["base_url"] = deploy_ai_base_url
    ai["model"] = deploy_ai_model

    email = load_json(src_cfg / "email.json")
    auth = load_json(src_cfg / "authentication.json")

    smtp = email.setdefault("smtp", {})
    smtp["host"] = "REPLACE_WITH_APPROVED_SMTP_HOST"
    smtp["sender"] = "REPLACE_WITH_APPROVED_SENDER"
    smtp["username"] = ""
    for key in list(smtp):
        if key.lower() in {"password", "passwd", "secret", "api_key"}:
            smtp.pop(key)

    email.setdefault("magic_link", {})["frontend_base_url"] = os.environ.get(
        "FORGE_FRONTEND_BASE_URL",
        "https://REPLACE-WITH-FORGE-HOST",
    ).strip().rstrip("/")

    token = auth.get("development_token", {})
    if not email["magic_link"]["frontend_base_url"].startswith(("http://", "https://")):
        raise SystemExit("ERROR: FORGE_FRONTEND_BASE_URL must be an HTTP(S) URL.")

    sanitized_auth = {
        "allowed_domains": auth.get("allowed_domains", []),
        "development_token": {
            "algorithm": token.get("algorithm", "HS256"),
            "expiration_minutes": token.get("expiration_minutes", 60),
        },
    }

    dst_cfg.mkdir(parents=True, exist_ok=True)
    for name, obj in (
        ("ai.json", ai),
        ("email.json", email),
        ("authentication.json", sanitized_auth),
    ):
        (dst_cfg / name).write_text(
            json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    item = commands.add_parser("ollama-config")
    item.add_argument("config")

    item = commands.add_parser("ollama-model")
    item.add_argument("tags_file")
    item.add_argument("model")

    item = commands.add_parser("runtime-email")
    item.add_argument("email_source")
    item.add_argument("runtime_config")

    item = commands.add_parser("stage-config")
    item.add_argument("source")
    item.add_argument("stage")
    item.add_argument("base_url")
    item.add_argument("model")

    args = parser.parse_args()
    if args.command == "ollama-config":
        ollama_config(args.config)
    elif args.command == "ollama-model":
        ollama_model(args.tags_file, args.model)
    elif args.command == "runtime-email":
        runtime_email(args.email_source, args.runtime_config)
    elif args.command == "stage-config":
        stage_config(args.source, args.stage, args.base_url, args.model)


if __name__ == "__main__":
    main()
