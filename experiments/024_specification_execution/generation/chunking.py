"""
FORGE Generation Core
Generation chunking.

This module divides an entity population into bounded work units.
It does not generate or persist data.
"""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_CHUNK_SIZE = 100_000


@dataclass(frozen=True)
class GenerationChunk:
    """A bounded unit of rows to be generated for one entity."""

    entity_name: str
    chunk_number: int
    start_row: int
    row_count: int

    @property
    def end_row(self) -> int:
        """Return the exclusive end row."""

        return self.start_row + self.row_count


def build_chunks(
    entity_name: str,
    total_rows: int,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[GenerationChunk, ...]:
    """
    Divide an entity population into bounded generation chunks.

    Example:
        250,000 rows with a chunk size of 100,000 produces:

        chunk 1 -> 100,000 rows
        chunk 2 -> 100,000 rows
        chunk 3 ->  50,000 rows
    """

    if not isinstance(entity_name, str) or not entity_name:
        raise ValueError("entity_name must be a non-empty string.")

    if (
        not isinstance(total_rows, int)
        or isinstance(total_rows, bool)
        or total_rows < 0
    ):
        raise ValueError(
            "total_rows must be a non-negative integer."
        )

    if (
        not isinstance(chunk_size, int)
        or isinstance(chunk_size, bool)
        or chunk_size <= 0
    ):
        raise ValueError(
            "chunk_size must be a positive integer."
        )

    chunks: list[GenerationChunk] = []

    start_row = 0
    chunk_number = 1

    while start_row < total_rows:
        row_count = min(
            chunk_size,
            total_rows - start_row,
        )

        chunks.append(
            GenerationChunk(
                entity_name=entity_name,
                chunk_number=chunk_number,
                start_row=start_row,
                row_count=row_count,
            )
        )

        start_row += row_count
        chunk_number += 1

    return tuple(chunks)
