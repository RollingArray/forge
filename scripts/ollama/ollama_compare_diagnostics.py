#!/usr/bin/env python3
"""
Compare the local and remote Ollama models using FORGE's existing diagnostics.

Run from the FORGE repository root:
  ./.venv/bin/python scripts/ollama/ollama_compare_diagnostics.py

Defaults:
  Local:  http://localhost:11434 / gpt-oss:20b
  Remote: http://10.254.231.222:11434 / gpt-oss-20b-jfrog:latest

The script does not modify ai.json or server configuration. It prints a
consolidated diagnostic transcript and saves it under backend/api/reports/ollama/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "backend" / "api" / "reports" / "ollama"
MODEL_DIAGNOSTIC = SCRIPTS_DIR / "ollama_model_diagnostics.py"
SEMANTIC_DIAGNOSTIC = SCRIPTS_DIR / "ollama_semantic_diagnostics.py"


def timestamp() -> str:
    return dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def emit(message: str, report_file) -> None:
    print(message, flush=True)
    report_file.write(message + "\n")
    report_file.flush()


def get_json(url: str, timeout: float = 10.0) -> tuple[int | None, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            try:
                return response.status, json.loads(body)
            except json.JSONDecodeError:
                return response.status, body
    except Exception as exc:
        return None, {"error": f"{type(exc).__name__}: {exc}"}


def model_metadata(base_url: str, model: str) -> Any:
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/show",
        data=json.dumps({"name": model}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        details = data.get("details") or {}
        model_info = data.get("model_info") or {}
        context_length = next(
            (v for k, v in model_info.items() if k.endswith("context_length")),
            None,
        )
        return {
            "family": details.get("family"),
            "parameter_size": details.get("parameter_size"),
            "quantization_level": details.get("quantization_level"),
            "format": details.get("format"),
            "capabilities": data.get("capabilities"),
            "context_length": context_length,
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def snapshot(base_url: str, model: str, label: str, emit_fn) -> None:
    base_url = base_url.rstrip("/")
    emit_fn(f"\n[{label}] Runtime snapshot at {timestamp()}")

    _, version = get_json(base_url + "/api/version")
    emit_fn(f"  version: {json.dumps(version, ensure_ascii=False)}")

    metadata = model_metadata(base_url, model)
    emit_fn(f"  model_metadata: {json.dumps(metadata, ensure_ascii=False)}")

    _, ps = get_json(base_url + "/api/ps")
    if isinstance(ps, dict):
        active = [
            {
                "name": item.get("name"),
                "size": item.get("size"),
                "size_vram": item.get("size_vram"),
                "context_length": item.get("context_length"),
                "expires_at": item.get("expires_at"),
                "runner": item.get("runner"),
            }
            for item in ps.get("models", [])
        ]
        emit_fn(f"  resident_models: {json.dumps(active, ensure_ascii=False)}")
        emit_fn(
            "  target_model_resident: "
            + str(any(item.get("name") == model for item in active))
        )
    else:
        emit_fn(f"  resident_models_error: {json.dumps(ps, ensure_ascii=False)}")


def run_command(
    command: list[str],
    label: str,
    emit_fn,
    timeout: int,
    env: dict[str, str] | None = None,
) -> int:
    emit_fn("\n" + "=" * 78)
    emit_fn(label)
    emit_fn("$ " + " ".join(command))
    emit_fn("=" * 78)
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
            env=env if env is not None else os.environ.copy(),
        )
        output = completed.stdout.rstrip()
        if output:
            for line in output.splitlines():
                emit_fn(line)
        emit_fn(f"\n[process exit code: {completed.returncode}]")
        return completed.returncode
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        if partial:
            for line in partial.splitlines():
                emit_fn(line)
        emit_fn(f"[TIMEOUT after {timeout} seconds]")
        return 124
    except Exception as exc:
        emit_fn(f"[EXECUTION ERROR] {type(exc).__name__}: {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare local and remote Ollama models with FORGE diagnostics."
    )
    parser.add_argument("--local-url", default="http://localhost:11434")
    parser.add_argument("--local-model", default="gpt-oss:20b")
    parser.add_argument("--remote-url", default="http://10.254.231.222:11434")
    parser.add_argument("--remote-model", default="gpt-oss-20b-jfrog:latest")
    parser.add_argument("--target", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-request timeout passed to the existing diagnostics.",
    )
    parser.add_argument(
        "--command-timeout",
        type=int,
        default=1800,
        help="Maximum runtime for each diagnostic script.",
    )
    parser.add_argument("--skip-semantic", action="store_true")
    parser.add_argument(
        "--skip-model-diagnostics",
        action="store_true",
        help="Skip chat/JSON/schema tests and run semantic diagnostics only.",
    )
    parser.add_argument("--pause-between-models", type=int, default=5)
    args = parser.parse_args()

    if not MODEL_DIAGNOSTIC.is_file():
        print(f"Missing diagnostic script: {MODEL_DIAGNOSTIC}", file=sys.stderr)
        return 2
    if not args.skip_semantic and not SEMANTIC_DIAGNOSTIC.is_file():
        print(
            f"Missing semantic diagnostic script: {SEMANTIC_DIAGNOSTIC}",
            file=sys.stderr,
        )
        return 2

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"ollama_comparison_{stamp}.txt"
    results: list[dict[str, Any]] = []

    configurations = [
        ("LOCAL", args.local_url.rstrip("/"), args.local_model),
        ("REMOTE", args.remote_url.rstrip("/"), args.remote_model),
    ]

    with report_path.open("w", encoding="utf-8") as report:

        def log(message: str) -> None:
            emit(message, report)

        log("=" * 78)
        log("FORGE LOCAL vs REMOTE OLLAMA DIAGNOSTIC COMPARISON")
        log("=" * 78)
        log(f"Started: {timestamp()}")
        log(f"Repository: {ROOT}")
        log(f"Local endpoint/model:  {args.local_url} | {args.local_model}")
        log(f"Remote endpoint/model: {args.remote_url} | {args.remote_model}")
        log(f"Semantic target/batch: {args.target}/{args.batch_size}")
        log(f"Per-request timeout: {args.timeout}s")
        log("No ai.json or Ollama server configuration is modified.")

        for index, (label, base_url, model) in enumerate(configurations):
            log("\n" + "#" * 78)
            log(f"{label} MODEL: {model}")
            log(f"Endpoint: {base_url}")
            log("#" * 78)
            snapshot(base_url, model, label + " BEFORE TESTS", log)

            if args.skip_model_diagnostics:
                model_code = None
                log(f"\n{label}: protocol diagnostics skipped by request.")
            else:
                model_code = run_command(
                    [
                        sys.executable,
                        str(MODEL_DIAGNOSTIC),
                        "--url",
                        base_url,
                        "--models",
                        model,
                        "--timeout",
                        str(args.timeout),
                    ],
                    f"{label}: BASIC CHAT / JSON MODE / JSON SCHEMA",
                    log,
                    args.command_timeout,
                )
                snapshot(base_url, model, label + " AFTER MODEL DIAGNOSTICS", log)

            semantic_code = None
            if not args.skip_semantic:
                semantic_env = os.environ.copy()
                backend_api_path = str(ROOT / "backend" / "api")
                existing_pythonpath = semantic_env.get("PYTHONPATH", "")
                semantic_env["PYTHONPATH"] = backend_api_path + (
                    os.pathsep + existing_pythonpath if existing_pythonpath else ""
                )
                semantic_code = run_command(
                    [
                        sys.executable,
                        str(SEMANTIC_DIAGNOSTIC),
                        "--url",
                        base_url,
                        "--model",
                        model,
                        "--target",
                        str(args.target),
                        "--batch-size",
                        str(args.batch_size),
                        "--timeout",
                        str(args.timeout),
                    ],
                    f"{label}: FORGE PRODUCTION SEMANTIC GENERATION",
                    log,
                    args.command_timeout,
                    env=semantic_env,
                )
                snapshot(base_url, model, label + " AFTER SEMANTIC DIAGNOSTICS", log)

            results.append(
                {
                    "label": label,
                    "model": model,
                    "model_diagnostics_exit_code": model_code,
                    "semantic_diagnostics_exit_code": semantic_code,
                }
            )

            if index == 0 and args.pause_between_models > 0:
                log(
                    f"\nPausing {args.pause_between_models}s before the remote tests..."
                )
                time.sleep(args.pause_between_models)

        log("\n" + "=" * 78)
        log("COMPARISON SUMMARY")
        log("=" * 78)
        for result in results:
            if result["model_diagnostics_exit_code"] is None:
                model_status = "SKIPPED"
            else:
                model_status = (
                    "PASS" if result["model_diagnostics_exit_code"] == 0 else "FAIL"
                )
            if result["semantic_diagnostics_exit_code"] is None:
                semantic_status = "SKIPPED"
            else:
                semantic_status = (
                    "PASS" if result["semantic_diagnostics_exit_code"] == 0 else "FAIL"
                )
            log(
                f"{result['label']} | {result['model']} | "
                f"protocol diagnostics: {model_status} | "
                f"semantic diagnostics: {semantic_status}"
            )

        log("\nInterpretation notes:")
        log("- Compare load_duration, prompt_eval_duration and eval_duration.")
        log("- Ollama reports these duration fields in nanoseconds.")
        log("- Compare target_model_resident snapshots before and after each phase.")
        log("- Functional PASS does not establish semantic correctness of every value.")
        log("- Other users/processes on either server can affect the comparison.")
        log(f"\nFull report saved to: {report_path}")
        log(f"Completed: {timestamp()}")

    print(f"\nReport file: {report_path}")
    return (
        1
        if any(
            item["model_diagnostics_exit_code"] not in (None, 0)
            or item["semantic_diagnostics_exit_code"] not in (None, 0)
            for item in results
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
