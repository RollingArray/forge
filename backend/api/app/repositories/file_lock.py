"""
File: file_lock.py
Purpose: Cross-platform process-level file locking for FORGE repositories.

Uses native operating-system locking APIs to coordinate repository access
between independent FORGE processes on Unix-like and Windows systems.
"""

import errno
import os
import time
from pathlib import Path
from typing import Self


class CrossPlatformFileLock:
    """
    Manage an exclusive process-level lock for a repository file path.

    The lock is acquired explicitly or through context-manager entry and
    released when the context exits.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = None

    def acquire(self) -> Self:
        """
        Acquire the exclusive operating-system lock.

        Unix-like systems use blocking flock operations. Windows retries
        non-blocking byte-range lock attempts until the lock is available.
        """

        if self._file is not None:
            raise RuntimeError("File lock is already acquired.")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.path.open("a+b")

        try:
            if os.name == "nt":
                import msvcrt

                # Windows byte-range locks require a byte to exist.
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()

                lock_file.seek(0)

                # LK_NBLCK is non-blocking. Retry until the lock is available.
                while True:
                    try:
                        msvcrt.locking(
                            lock_file.fileno(),
                            msvcrt.LK_NBLCK,
                            1,
                        )
                        break
                    except OSError as exc:
                        if exc.errno not in (
                            errno.EACCES,
                            errno.EAGAIN,
                            errno.EDEADLK,
                        ):
                            raise
                        time.sleep(0.05)
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            self._file = lock_file
            return self

        except BaseException:
            lock_file.close()
            raise

    def release(self) -> None:
        """
        Release the operating-system lock and close its lock file.

        Calling release when this instance does not hold a lock is a no-op.
        """

        lock_file = self._file
        if lock_file is None:
            return

        self._file = None

        try:
            if os.name == "nt":
                import msvcrt

                lock_file.seek(0)
                msvcrt.locking(
                    lock_file.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )
            else:
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()

    def __enter__(self) -> Self:
        """Acquire the lock when entering a context manager."""
        return self.acquire()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Release the lock when leaving a context manager."""
        self.release()


def create_file_lock(path: Path) -> CrossPlatformFileLock:
    """Return an unacquired process-safe lock for the specified path."""

    return CrossPlatformFileLock(path)
