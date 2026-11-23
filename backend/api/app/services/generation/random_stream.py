"""
Stable, independently derived random streams for FORGE generation.

A stream is identified by the generation seed, algorithm version,
entity, field or relationship scope, global row number, and purpose.
"""

from __future__ import annotations

import hashlib
import json
import random


_DERIVATION_VERSION = "forge-random-stream-v1"


def derive_random_seed(
    *,
    base_seed: int,
    algorithm_version: str,
    entity_name: str,
    scope: str,
    row_number: int,
    purpose: str,
) -> int:
    """
    Derive a stable integer seed for one generation operation.

    `scope` identifies a field or relationship.
    `row_number` is the one-based global entity row number.
    """

    if isinstance(base_seed, bool) or not isinstance(base_seed, int):
        raise ValueError("base_seed must be an integer.")

    if isinstance(row_number, bool) or not isinstance(row_number, int):
        raise ValueError("row_number must be an integer.")

    if row_number < 1:
        raise ValueError("row_number must be greater than zero.")

    values = {
        "derivation_version": _DERIVATION_VERSION,
        "algorithm_version": algorithm_version,
        "base_seed": base_seed,
        "entity_name": entity_name,
        "scope": scope,
        "row_number": row_number,
        "purpose": purpose,
    }

    for name in (
        "algorithm_version",
        "entity_name",
        "scope",
        "purpose",
    ):
        value = values[name]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string.")

    canonical = json.dumps(
        values,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    digest = hashlib.sha256(canonical).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def create_random_stream(
    *,
    base_seed: int,
    algorithm_version: str,
    entity_name: str,
    scope: str,
    row_number: int,
    purpose: str,
) -> random.Random:
    """Create an independent deterministic random stream."""

    derived_seed = derive_random_seed(
        base_seed=base_seed,
        algorithm_version=algorithm_version,
        entity_name=entity_name,
        scope=scope,
        row_number=row_number,
        purpose=purpose,
    )

    return random.Random(derived_seed)
