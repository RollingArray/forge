"""Cross-process lifecycle transition locks for generation jobs."""

from __future__ import annotations

from contextlib import contextmanager
import math
from pathlib import Path
from typing import Iterator

from app.repositories.file_lock import file_lock_transaction


def lifecycle_transition_lock_path(job_directory: Path) -> Path:
    """Return the stable lifecycle transition lock-file path."""
    return Path(job_directory) / ".locks" / "lifecycle.transition.lock"


@contextmanager
def generation_job_transition_lock(
    job_directory: Path,
    *,
    timeout: float | None = 30.0,
) -> Iterator[None]:
    """Hold the per-job lifecycle transition lock.

    This lock is separate from the execution lease and is intended for
    short-lived durable state transitions only.

    The lock file is persistent and must never be deleted or replaced.
    """
    if timeout is not None:
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout < 0
        ):
            raise ValueError(
                "Lifecycle transition lock timeout must be non-negative."
            )

    lock_path = lifecycle_transition_lock_path(job_directory)

    with file_lock_transaction(lock_path, timeout=timeout):
        yield
