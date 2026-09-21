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


def get_chunk_output_path(
    output_directory: str | Path,
    entity_name: str,
    chunk_number: int,
) -> Path:
    """
    Return the deterministic durable path for one entity chunk.

    Chunk files live below an entity-specific directory so that
    the final ENTITY.csv can remain the user-facing dataset artifact.
    """

    if chunk_number < 1:
        raise ValueError(
            "chunk_number must be greater than or equal to 1."
        )

    return (
        Path(output_directory)
        / entity_name
        / "chunks"
        / f"chunk_{chunk_number:06d}.csv"
    )


def write_chunk_atomically(
    output_path: str | Path,
    rows: list[dict[str, Any]],
) -> Path:
    """
    Write one generation chunk durably and atomically.

    The chunk is first written to a temporary file in the same
    directory as the destination. The temporary file is flushed
    and fsynced before being atomically renamed to the final path.
    """

    path = Path(output_path)

    if not isinstance(rows, list):
        raise ValueError("rows must be a list.")

    if not rows:
        raise ValueError("Cannot commit an empty generation chunk.")

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    field_names = list(rows[0].keys())

    temporary_path = path.with_name(
        f".{path.name}.tmp"
    )

    try:
        with temporary_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=field_names,
            )

            writer.writeheader()
            writer.writerows(rows)

            file.flush()
            import os

            os.fsync(file.fileno())

        import os

        os.replace(
            temporary_path,
            path,
        )

        try:
            directory_fd = os.open(
                path.parent,
                os.O_RDONLY,
            )

            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        except OSError:
            # Some filesystems do not support directory fsync.
            # The file itself has already been flushed and atomically
            # replaced.
            pass

    except Exception:
        temporary_path.unlink(
            missing_ok=True,
        )
        raise

    return path


def read_rows(
    output_path: str | Path,
) -> list[dict[str, Any]]:
    """Read previously committed entity rows from a CSV file."""

    path = Path(output_path)

    if not path.exists():
        return []

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)
        return list(reader)


def assemble_entity_output(
    *,
    output_directory: str | Path,
    entity_name: str,
) -> Path:
    """
    Assemble committed entity chunks into the final ENTITY.csv.

    Chunks remain durable after assembly. The final CSV is a
    user-facing dataset artifact derived from those committed chunks.
    """

    output_root = Path(output_directory)

    chunk_directory = (
        output_root
        / entity_name
        / "chunks"
    )

    if not chunk_directory.exists():
        raise FileNotFoundError(
            f"Chunk directory does not exist for entity "
            f"{entity_name!r}: {chunk_directory}"
        )

    chunk_paths = sorted(
        chunk_directory.glob("chunk_*.csv")
    )

    if not chunk_paths:
        raise FileNotFoundError(
            f"No committed chunks found for entity "
            f"{entity_name!r}: {chunk_directory}"
        )

    final_path = get_entity_output_path(
        output_directory=output_root,
        entity_name=entity_name,
    )

    temporary_path = final_path.with_name(
        f".{final_path.name}.tmp"
    )

    try:
        with temporary_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as output_file:

            writer = None

            for chunk_path in chunk_paths:
                with chunk_path.open(
                    "r",
                    newline="",
                    encoding="utf-8",
                ) as chunk_file:

                    reader = csv.DictReader(chunk_file)

                    if reader.fieldnames is None:
                        raise ValueError(
                            f"Committed chunk has no header: "
                            f"{chunk_path}"
                        )

                    if writer is None:
                        writer = csv.DictWriter(
                            output_file,
                            fieldnames=reader.fieldnames,
                        )
                        writer.writeheader()

                    elif list(reader.fieldnames) != list(
                        writer.fieldnames
                    ):
                        raise ValueError(
                            f"Schema mismatch while assembling "
                            f"{entity_name!r}: {chunk_path}"
                        )

                    for row in reader:
                        writer.writerow(row)

            if writer is None:
                raise ValueError(
                    f"No rows found while assembling entity "
                    f"{entity_name!r}."
                )

            output_file.flush()

            import os

            os.fsync(output_file.fileno())

        import os

        os.replace(
            temporary_path,
            final_path,
        )

        try:
            directory_fd = os.open(
                final_path.parent,
                os.O_RDONLY,
            )

            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        except OSError:
            # The file itself has already been atomically replaced.
            pass

    except Exception:
        temporary_path.unlink(
            missing_ok=True,
        )
        raise

    return final_path


def get_entity_output_path(
    output_directory: str | Path,
    entity_name: str,
) -> Path:
    """Return the CSV output path for one entity."""

    if not isinstance(entity_name, str) or not entity_name:
        raise ValueError("entity_name must be a non-empty string.")

    return Path(output_directory) / f"{entity_name}.csv"
