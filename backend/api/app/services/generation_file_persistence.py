"""
Shared, cross-platform persistence primitives for generation state files.
"""

from __future__ import annotations

import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Lock, RLock
from typing import Iterator

from app.repositories.file_lock import create_file_lock


_registry_guard = Lock()
_path_locks: dict[str, RLock] = {}

_REPLACE_RETRIES = 4
_REPLACE_RETRY_DELAY_SECONDS = 0.05
_TRANSIENT_WINDOWS_ERRORS = {32, 33}


@contextmanager
def generation_file_lock(path: Path) -> Iterator[None]:
    """
    Serialize access to one generation file across threads and processes.

    All readers and writers of a destination must use this same lock.
    """

    lock_path = (
        path.parent
        / ".locks"
        / f"{path.name}.lock"
    )
    lock_key = str(lock_path.resolve())

    with _registry_guard:
        thread_lock = _path_locks.setdefault(
            lock_key,
            RLock(),
        )

    with thread_lock:
        with create_file_lock(lock_path):
            yield


def atomic_write_text(path: Path, content: str) -> None:
    """
    Atomically replace a text file using a unique temporary file.

    The caller is responsible for acquiring generation_file_lock(path).
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        for attempt in range(_REPLACE_RETRIES + 1):
            try:
                os.replace(temporary_path, path)
                break
            except OSError as exc:
                is_transient_windows_error = (
                    os.name == "nt"
                    and getattr(exc, "winerror", None)
                    in _TRANSIENT_WINDOWS_ERRORS
                )

                if (
                    not is_transient_windows_error
                    or attempt >= _REPLACE_RETRIES
                ):
                    raise

                time.sleep(
                    _REPLACE_RETRY_DELAY_SECONDS * (2 ** attempt)
                )

    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
