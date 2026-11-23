"""Cross-process execution leases for generation jobs."""

from __future__ import annotations

from contextlib import contextmanager
import math
from pathlib import Path
from typing import Iterator

from app.repositories.file_lock import file_lock_transaction


def execution_lease_lock_path(job_directory: Path) -> Path:
    """Return the stable execution lease lock-file path for one job."""
    return Path(job_directory) / ".locks" / "execution.lease.lock"


@contextmanager
def generation_execution_lease(
    job_directory: Path,
    *,
    timeout: float | None = 0.0,
) -> Iterator[None]:
    """Hold an OS-managed execution lease for the lifetime of the context.

    The lock file is persistent. Never delete or replace it, as doing so
    could allow independent processes to lock different files for one job.

    The default timeout is zero (nonblocking). Pass None for an
    indefinitely blocking acquisition.
    """
    if timeout is not None:
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout < 0
        ):
            raise ValueError("Execution lease timeout must be non-negative.")

    lock_path = execution_lease_lock_path(job_directory)

    with file_lock_transaction(lock_path, timeout=timeout):
        yield
