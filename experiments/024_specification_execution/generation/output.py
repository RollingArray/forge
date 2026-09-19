"""
FORGE Generation Core
Generation output persistence.

This module is UI-independent.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def write_rows(
    output_path: str | Path,
    rows: list[dict[str, Any]],
) -> None:
    """Write one generated chunk of rows to a CSV file."""

    path = Path(output_path)

    if not isinstance(rows, list):
        raise ValueError("rows must be a list.")

    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    field_names = list(rows[0].keys())
    write_header = not path.exists()

    with path.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=field_names,
        )

        if write_header:
            writer.writeheader()

        writer.writerows(rows)


def get_entity_output_path(
    output_directory: str | Path,
    entity_name: str,
) -> Path:
    """Return the CSV output path for one entity."""

    if not isinstance(entity_name, str) or not entity_name:
        raise ValueError("entity_name must be a non-empty string.")

    return Path(output_directory) / f"{entity_name}.csv"
