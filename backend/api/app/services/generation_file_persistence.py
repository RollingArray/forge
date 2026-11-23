"""
Shared, cross-platform persistence primitives for generation state files.
"""

from __future__ import annotations

import errno
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, TextIO

from app.repositories.file_lock import file_lock_transaction

_REPLACE_RETRIES = 4
_REPLACE_RETRY_DELAY_SECONDS = 0.05
_TRANSIENT_WINDOWS_ERRORS = {32, 33}

_UNSUPPORTED_DIRECTORY_SYNC_ERRORS = {
    errno.EINVAL,
    errno.ENOSYS,
    getattr(errno, "ENOTSUP", errno.EINVAL),
    getattr(errno, "EOPNOTSUPP", errno.EINVAL),
}


def _sync_directory(directory: Path) -> None:
    """Sync directory-entry metadata where the platform supports it."""
    if os.name == "nt":
        return

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)

    try:
        directory_fd = os.open(directory, flags)
    except OSError as exc:
        if exc.errno in _UNSUPPORTED_DIRECTORY_SYNC_ERRORS:
            return
        raise

    try:
        try:
            os.fsync(directory_fd)
        except OSError as exc:
            if exc.errno not in _UNSUPPORTED_DIRECTORY_SYNC_ERRORS:
                raise
    finally:
        os.close(directory_fd)


@contextmanager
def generation_file_lock(path: Path) -> Iterator[None]:
    """Serialize access to one generation file across threads and processes."""
    lock_path = (
        path.parent
        / ".locks"
        / f"{path.name}.lock"
    )

    with file_lock_transaction(lock_path):
        yield


def atomic_write_file(
    path: Path,
    write_content: Callable[[TextIO], None],
) -> None:
    """
    Atomically publish a text file using a unique same-directory temp file.

    The callback writes to the temporary file. The file is flushed and
    fsynced before replacement. The destination is never opened for writing.
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
            newline="",
        ) as handle:
            write_content(handle)
            handle.flush()
            os.fsync(handle.fileno())

        for attempt in range(_REPLACE_RETRIES + 1):
            try:
                os.replace(temporary_path, path)
                _sync_directory(path.parent)
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


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a text file using a unique temporary file."""
    atomic_write_file(
        path,
        lambda handle: handle.write(content),
    )
