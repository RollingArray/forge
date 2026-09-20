"""
FORGE Generation Core
CLI progress reporting.

This module is intentionally independent of generation and execution logic.
"""

from __future__ import annotations

import sys
import time
from typing import TextIO


class CLIProgressReporter:
    """Render live generation progress in a terminal."""

    def __init__(
        self,
        total_target_rows: int,
        output: TextIO | None = None,
    ) -> None:
        self.total_target_rows = max(total_target_rows, 0)
        self.output = output or sys.stdout

        self.started_at = time.monotonic()

        self.current_entity: str | None = None
        self.current_target_rows = 0
        self.current_generated_rows = 0
        self.current_chunk = 0
        self.total_chunks = 0

        self._overall_generated = 0
        self._active = False

    def start_entity(
        self,
        entity_name: str,
        target_rows: int,
        total_chunks: int,
    ) -> None:
        self.current_entity = entity_name
        self.current_target_rows = max(target_rows, 0)
        self.current_generated_rows = 0
        self.current_chunk = 0
        self.total_chunks = max(total_chunks, 0)
        self._active = True

    def update_chunk(
        self,
        chunk_number: int,
        generated_rows: int,
        total_generated_rows: int,
    ) -> None:
        self.current_chunk = chunk_number

        self.current_generated_rows = min(
            max(generated_rows, 0),
            self.current_target_rows,
        )

        self._overall_generated = min(
            max(total_generated_rows, 0),
            self.total_target_rows,
        )

        elapsed = max(
            time.monotonic() - self.started_at,
            0.001,
        )

        entity_progress = (
            self.current_generated_rows / self.current_target_rows
            if self.current_target_rows
            else 0.0
        )

        overall_progress = (
            self._overall_generated / self.total_target_rows
            if self.total_target_rows
            else 0.0
        )

        throughput = self._overall_generated / elapsed

        line = (
            f"  > {self.current_entity:<22} "
            f"chunk {self.current_chunk:>5}/{self.total_chunks:<5} | "
            f"entity {self.current_generated_rows:>9,}/"
            f"{self.current_target_rows:<9,} "
            f"({entity_progress:>6.1%}) | "
            f"overall {self._overall_generated:>10,}/"
            f"{self.total_target_rows:<10,} "
            f"({overall_progress:>6.1%}) | "
            f"{throughput:>10,.0f} rows/s | "
            f"{self._format_elapsed(elapsed)}"
        )

        self._write_live(line)

    def complete_entity(
        self,
        entity_name: str,
        generated_rows: int,
    ) -> None:
        self.current_entity = entity_name
        self.current_generated_rows = max(generated_rows, 0)

        # This is a safeguard for callers that complete an entity without
        # sending a final chunk update.
        self._overall_generated = min(
            max(self._overall_generated, generated_rows),
            self.total_target_rows,
        )

        elapsed = max(
            time.monotonic() - self.started_at,
            0.001,
        )

        throughput = self.current_generated_rows / elapsed

        self._clear_live_line()

        self.output.write(
            f"  ✓ {entity_name:<22} "
            f"{self.current_generated_rows:>10,} rows | "
            f"{throughput:>10,.0f} rows/s\n"
        )
        self.output.flush()

        self._active = False

    def fail_entity(
        self,
        entity_name: str,
        error: str,
    ) -> None:
        self._clear_live_line()

        self.output.write(
            f"  ✗ {entity_name}: {error}\n"
        )
        self.output.flush()

        self._active = False

    def finish(self) -> None:
        if self._active:
            self._clear_live_line()

        elapsed = max(
            time.monotonic() - self.started_at,
            0.001,
        )

        throughput = self._overall_generated / elapsed

        self.output.write(
            f"  Overall throughput: "
            f"{throughput:,.0f} rows/s | "
            f"Elapsed: {self._format_elapsed(elapsed)}\n"
        )
        self.output.flush()

        self._active = False

    def _write_live(self, line: str) -> None:
        self._clear_live_line()
        self.output.write("\r" + line)
        self.output.flush()

    def _clear_live_line(self) -> None:
        if hasattr(self.output, "isatty") and self.output.isatty():
            self.output.write("\r\033[2K")

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        total_seconds = int(seconds)

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return f"{minutes:02d}:{seconds:02d}"
