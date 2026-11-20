import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_URL = "http://10.254.231.222:11434"

SCHEMA = {
    "type": "object",
    "properties": {
        "values": {
            "type": "array",
            "items": {"type": "string"},
        }
    },
    "required": ["values"],
    "additionalProperties": False,
}

PROMPT = (
    'Generate exactly 3 unique country names. '
    'Return a JSON object with a "values" array containing '
    'exactly 3 strings. Return no other content.'
)


def request_json(url, payload=None, timeout=60):
    headers = {"Content-Type": "application/json"}
    data = None if payload is None else json.dumps(payload).encode()

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="GET" if payload is None else "POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def get_model_details(base_url, model, timeout):
    return request_json(
        f"{base_url}/api/show",
        {"model": model},
        timeout,
    )


def response_metrics(data):
    def seconds(key):
        return round(data.get(key, 0) / 1_000_000_000, 3)

    eval_duration = data.get("eval_duration", 0)
    eval_count = data.get("eval_count", 0)

    tokens_per_second = (
        round(eval_count / (eval_duration / 1_000_000_000), 2)
        if eval_duration else None
    )

    return {
        "total_seconds": seconds("total_duration"),
        "load_seconds": seconds("load_duration"),
        "prompt_eval_seconds": seconds("prompt_eval_duration"),
        "eval_seconds": seconds("eval_duration"),
        "eval_count": eval_count,
        "tokens_per_second": tokens_per_second,
    }


def run_chat_test(base_url, model, test_name, payload, timeout):
    started = time.monotonic()

    result = {
        "test": test_name,
        "status": "FAIL",
        "elapsed_seconds": None,
        "response": None,
        "error": None,
        "metrics": {},
    }

    try:
        data = request_json(
            f"{base_url}/api/chat",
            payload,
            timeout,
        )

        content = data.get("message", {}).get("content", "")
        result["response"] = content
        result["metrics"] = response_metrics(data)

        markers = [
            "<|turn>",
            "<|im_start|>",
            "<|im_end|>",
            "<|vision_start|>",
            "<|end|>",
            "<|start|>",
            "<|channel|>",
            "<|message|>",
            "<|assistant|>",
        ]

        result["conversation_marker_leak"] = any(
            marker in content for marker in markers
        )

        result["done"] = data.get("done")

        if test_name == "basic_chat":
            result["status"] = (
                "PASS"
                if content.strip() == "FORGE_CHAT_OK"
                and not result["conversation_marker_leak"]
                else "FAIL"
            )

        else:
            try:
                parsed = json.loads(content)
                values = parsed.get("values")

                result["parsed_json"] = True
                result["values_count"] = (
                    len(values) if isinstance(values, list) else None
                )
                result["values_are_strings"] = (
                    isinstance(values, list)
                    and all(
                        isinstance(value, str) and value.strip()
                        for value in values
                    )
                )
                result["unique_values"] = (
                    len({value.casefold() for value in values})
                    if isinstance(values, list)
                    and all(isinstance(value, str) for value in values)
                    else None
                )

                valid = (
                    isinstance(parsed, dict)
                    and isinstance(values, list)
                    and len(values) == 3
                    and result["values_are_strings"]
                    and result["unique_values"] == 3
                )

                result["status"] = (
                    "PASS"
                    if valid and not result["conversation_marker_leak"]
                    else "FAIL"
                )

            except (json.JSONDecodeError, AttributeError):
                result["parsed_json"] = False
                result["status"] = "FAIL"

    except Exception as exc:
        result["error"] = str(exc)

    result["elapsed_seconds"] = round(
        time.monotonic() - started, 3
    )

    return result


def test_model(base_url, model, timeout):
    print("\n" + "=" * 75)
    print(f"MODEL: {model}")
    print("=" * 75)

    report = {
        "model": model,
        "metadata": {},
        "tests": [],
    }

    try:
        details = get_model_details(base_url, model, timeout)

        report["metadata"] = {
            "details": details.get("details"),
            "template": details.get("template"),
            "parameters": details.get("parameters"),
            "capabilities": details.get("capabilities"),
        }

        print("Family:", details.get("details", {}).get("family"))
        print("Parameters:", details.get("details", {}).get("parameter_size"))
        print("Quantization:", details.get("details", {}).get("quantization_level"))
        print("Template:", details.get("template"))

    except Exception as exc:
        report["metadata_error"] = str(exc)
        print("METADATA ERROR:", exc)
        return report

    tests = [
        (
            "basic_chat",
            {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a test assistant.",
                    },
                    {
                        "role": "user",
                        "content": "Reply with exactly FORGE_CHAT_OK",
                    },
                ],
                "stream": False,
                "options": {"temperature": 0},
            },
        ),
        (
            "json_mode",
            {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only valid JSON.",
                    },
                    {"role": "user", "content": PROMPT},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
        ),
        (
            "json_schema",
            {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a structured data generation service. "
                            "Follow the supplied JSON schema exactly."
                        ),
                    },
                    {"role": "user", "content": PROMPT},
                ],
                "stream": False,
                "format": SCHEMA,
                "options": {"temperature": 0},
            },
        ),
    ]

    for test_name, payload in tests:
        print(f"\nRunning: {test_name}")

        result = run_chat_test(
            base_url, model, test_name, payload, timeout
        )

        report["tests"].append(result)

        print("Status:", result["status"])
        print("Elapsed:", result["elapsed_seconds"], "seconds")

        if result["metrics"]:
            print("Metrics:", result["metrics"])

        if result.get("error"):
            print("Error:", result["error"])

        if result.get("response") is not None:
            print("Response:", repr(result["response"][:1500]))

    return report


def main():
    parser = argparse.ArgumentParser(
        description="FORGE Ollama model diagnostic runner"
    )

    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Ollama server URL",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["gpt-oss-20b:latest", "gemma4:12b"],
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
    )
    parser.add_argument(
        "--inventory-only",
        action="store_true",
    )

    args = parser.parse_args()
    base_url = args.url.rstrip("/")

    print("FORGE OLLAMA MODEL DIAGNOSTICS")
    print("Server:", base_url)

    try:
        inventory = request_json(
            f"{base_url}/api/tags",
            timeout=30,
        )
    except Exception as exc:
        raise SystemExit(f"Cannot connect to Ollama: {exc}")

    available = [
        item["name"] for item in inventory.get("models", [])
    ]

    print("\nAVAILABLE MODELS:")
    for name in available:
        print(" -", name)

    if args.inventory_only:
        return

    reports = []

    for model in args.models:
        if model not in available:
            print(f"\nSKIPPING: {model} is not available")
            reports.append({
                "model": model,
                "status": "NOT_AVAILABLE",
            })
            continue

        reports.append(
            test_model(base_url, model, args.timeout)
        )

    output_dir = Path("backend/api/reports/ollama")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = output_dir / f"model_diagnostics_{timestamp}.json"

    output_file.write_text(
        json.dumps(
            {
                "server": base_url,
                "timestamp_utc": timestamp,
                "reports": reports,
            },
            indent=2,
        )
    )

    print("\n" + "=" * 75)
    print("SUMMARY")
    print("=" * 75)

    for report in reports:
        print("\n", report["model"])

        for test in report.get("tests", []):
            print(
                f"  {test['test']}: {test['status']} "
                f"({test['elapsed_seconds']} sec)"
            )

    print("\nFull report:", output_file)


if __name__ == "__main__":
    main()
