import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Import the actual production prompt used by FORGE.
API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from app.prompts.semantic_prompt import SEMANTIC_GENERATION_SYSTEM_PROMPT


SCHEMA = {
    "type": "object",
    "properties": {
        "values": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["values"],
}

MARKERS = [
    "<|turn>",
    "<|im_start|>",
    "<|im_end|>",
    "<|end|>",
    "<|start|>",
    "<|channel|>",
    "<|message|>",
]


def call_ollama(base_url, model, requested, collected, timeout):
    user_content = (
        f"Mode: VOCABULARY\n"
        f"Count: {requested}\n"
        f"Description: Country name"
    )

    if collected:
        user_content += (
            "\nPreviously generated values (do not repeat):\n"
            + json.dumps(collected, ensure_ascii=False)
        )

    # Deliberately mirrors the production provider.
    # No temperature or other options are added.
    request_payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SEMANTIC_GENERATION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        "stream": False,
        "format": SCHEMA,
    }

    request = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    started = time.monotonic()

    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    elapsed = time.monotonic() - started

    message = payload.get("message")
    if not isinstance(message, dict):
        raise RuntimeError("Invalid Ollama chat response: missing message")

    raw = message.get("content")
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("Ollama returned empty content")

    return raw, elapsed, payload


def main():
    parser = argparse.ArgumentParser(
        description="FORGE production semantic-generation diagnostic"
    )
    parser.add_argument(
        "--url",
        default="http://10.254.231.222:11434",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Exact Ollama model name to test",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=50,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    collected = []
    collected_set = set()
    calls = []
    status = "INCOMPLETE"

    print("=" * 75)
    print("FORGE PRODUCTION SEMANTIC GENERATION DIAGNOSTIC")
    print("=" * 75)
    print("Server:", base_url)
    print("Model:", args.model)
    print("Mode: VOCABULARY")
    print("Description: Country name")
    print("Target:", args.target)
    print("Batch size:", args.batch_size)
    print("Inference options: Same as production (none explicitly supplied)")

    for call_number in range(1, 7):
        remaining = args.target - len(collected)

        if remaining <= 0:
            status = "PASS"
            break

        requested = min(args.batch_size, remaining)

        print("\n" + "-" * 75)
        print(f"CALL {call_number}")
        print("Requested:", requested)
        print("Previously accepted:", len(collected))

        started = time.monotonic()

        try:
            raw, elapsed, response = call_ollama(
                base_url,
                args.model,
                requested,
                collected,
                args.timeout,
            )

            print("Elapsed:", round(elapsed, 2), "seconds")
            print("Raw response:")
            print(raw)

            record = {
                "call": call_number,
                "requested": requested,
                "previously_accepted": len(collected),
                "elapsed_seconds": round(elapsed, 3),
                "raw_response": raw,
                "status": "FAIL",
            }

            record["conversation_marker_leak"] = any(
                marker in raw for marker in MARKERS
            )

            try:
                result = json.loads(raw)
            except json.JSONDecodeError as exc:
                record["error"] = (
                    f"JSONDecodeError: {exc}"
                )
                calls.append(record)
                print("FAIL: Invalid JSON")
                break

            if not isinstance(result, dict):
                record["error"] = "Response is not a JSON object"
                calls.append(record)
                print("FAIL: Invalid JSON structure")
                break

            values = result.get("values")

            if not isinstance(values, list):
                record["error"] = "Missing values array"
                calls.append(record)
                print("FAIL: Missing values array")
                break

            if not all(
                isinstance(value, str) and value.strip()
                for value in values
            ):
                record["error"] = "Invalid or empty STRING value"
                calls.append(record)
                print("FAIL: Invalid STRING values")
                break

            duplicates = 0
            new_unique = 0

            for value in values:
                normalized = value.strip()
                key = normalized.casefold()

                if key in collected_set:
                    duplicates += 1
                    continue

                if len(collected) >= args.target:
                    break

                collected_set.add(key)
                collected.append(normalized)
                new_unique += 1

            record.update({
                "returned": len(values),
                "exact_requested_count": len(values) == requested,
                "new_unique": new_unique,
                "duplicates": duplicates,
                "total_unique": len(collected),
                "conversation_marker_leak": record[
                    "conversation_marker_leak"
                ],
                "status": (
                    "PASS"
                    if len(values) == requested
                    and not record["conversation_marker_leak"]
                    else "FAIL"
                ),
                "ollama_total_duration_seconds": round(
                    response.get("total_duration", 0) / 1e9, 3
                ),
                "ollama_load_duration_seconds": round(
                    response.get("load_duration", 0) / 1e9, 3
                ),
                "ollama_eval_count": response.get("eval_count"),
            })

            calls.append(record)

            print("\nBatch results:")
            print("Returned:", len(values))
            print("New unique:", new_unique)
            print("Duplicates:", duplicates)
            print("Total unique:", len(collected))
            print("Batch status:", record["status"])

            if record["conversation_marker_leak"]:
                print("WARNING: Conversation marker leakage detected")
                break

        except Exception as exc:
            calls.append({
                "call": call_number,
                "requested": requested,
                "elapsed_seconds": round(
                    time.monotonic() - started, 3
                ),
                "status": "FAIL",
                "error": repr(exc),
            })
            print("ERROR:", repr(exc))
            break

    if len(collected) == args.target:
        status = "PASS"

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "server": base_url,
        "model": args.model,
        "mode": "VOCABULARY",
        "description": "Country name",
        "target": args.target,
        "batch_size": args.batch_size,
        "status": status,
        "total_unique": len(collected),
        "final_values": collected,
        "calls": calls,
    }

    output_dir = Path("backend/api/reports/ollama")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%d_%H%M%S"
    )
    output_file = output_dir / f"semantic_{timestamp}.json"

    output_file.write_text(json.dumps(report, indent=2))

    print("\n" + "=" * 75)
    print("FINAL RESULT:", status)
    print("Unique values:", len(collected), "/", args.target)
    print("API calls:", len(calls))
    print("Report:", output_file)
    print("=" * 75)


if __name__ == "__main__":
    main()
