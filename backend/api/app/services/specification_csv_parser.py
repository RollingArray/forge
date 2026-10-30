"""
Parse CSV text supplied by the FORGE Specification Wizard.

This module performs structural CSV parsing only. Specification
semantics and cross-reference validation belong to the import service.
"""

from __future__ import annotations

import csv
import io
from typing import Any


class SpecificationCsvParser:
    """Parse a CSV section using its canonical column contract."""

    @staticmethod
    def parse_section(
        section: str,
        content: str | None,
        expected_headers: tuple[str, ...],
        required_headers: tuple[str, ...],
    ) -> dict[str, Any]:
        """Return normalized rows and structural parsing errors."""

        if not isinstance(content, str) or not content.strip():
            return {
                "section": section,
                "headers": [],
                "rows": [],
                "errors": [],
            }

        stream = io.StringIO(
            content.removeprefix("\ufeff"),
            newline="",
        )
        reader = csv.reader(stream, strict=True)

        errors: list[dict[str, Any]] = []
        rows: list[dict[str, Any]] = []
        headers: list[str] = []

        try:
            header_row: list[str] | None = None

            for record in reader:
                if not record or all(
                    not value.strip() for value in record
                ):
                    continue

                header_row = record
                break

            if header_row is None:
                return {
                    "section": section,
                    "headers": [],
                    "rows": [],
                    "errors": [],
                }

            headers = [
                value.strip().lower()
                for value in header_row
            ]

            if any(not header for header in headers):
                errors.append({
                    "row": 1,
                    "column": None,
                    "message": "CSV headers must not be empty.",
                })

            duplicates = sorted({
                header
                for header in headers
                if header and headers.count(header) > 1
            })

            for header in duplicates:
                errors.append({
                    "row": 1,
                    "column": header,
                    "message": f"Duplicate CSV header: {header}.",
                })

            unexpected = [
                header
                for header in headers
                if header and header not in expected_headers
            ]

            for header in unexpected:
                errors.append({
                    "row": 1,
                    "column": header,
                    "message": f"Unexpected CSV column: {header}.",
                })

            missing = [
                header
                for header in required_headers
                if header not in headers
            ]

            for header in missing:
                errors.append({
                    "row": 1,
                    "column": header,
                    "message": f"Required CSV column is missing: {header}.",
                })

            if errors:
                return {
                    "section": section,
                    "headers": headers,
                    "rows": [],
                    "errors": errors,
                }

            previous_line = reader.line_num

            for record in reader:
                start_line = previous_line + 1
                previous_line = reader.line_num

                if not record or all(
                    not value.strip() for value in record
                ):
                    continue

                if len(record) != len(headers):
                    errors.append({
                        "row": start_line,
                        "column": None,
                        "message": (
                            f"Expected {len(headers)} values but found "
                            f"{len(record)}."
                        ),
                    })
                    continue

                values = {
                    header: value.strip()
                    for header, value in zip(headers, record)
                }

                rows.append({
                    "row_number": start_line,
                    "values": values,
                })

        except csv.Error as exc:
            errors.append({
                "row": reader.line_num or 1,
                "column": None,
                "message": f"Invalid CSV syntax: {exc}",
            })

        return {
            "section": section,
            "headers": headers,
            "rows": rows,
            "errors": errors,
        }
