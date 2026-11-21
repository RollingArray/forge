"""
File: file_lock.py
Purpose: Cross-platform thread and process locking for FORGE repositories.

Uses native operating-system locking APIs to coordinate repository access
between independent FORGE processes on Unix-like and Windows systems.

file_lock_transaction() provides:
- Shared per-path thread locking.
- Cross-process operating-system locking.
- Safe nested transactions within the same thread.
- Bounded acquisition with an explicit timeout.
"""

import errno
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Self


_RETRY_INTERVAL_SECONDS = 0.05
_DEFAULT_TRANSACTION_TIMEOUT_SECONDS = 30.0


class FileLockTimeout(TimeoutError):
    """Raised when a file lock cannot be acquired before its deadline."""


class CrossPlatformFileLock:
    """
    Manage an exclusive process-level lock for a repository file path.

    The lock is acquired explicitly or through context-manager entry and
    released when the context exits.

    Passing no timeout preserves the original blocking behavior.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._file = None

    def acquire(self, timeout: float | None = None) -> Self:
        """Acquire the exclusive operating-system lock."""

        if self._file is not None:
            raise RuntimeError("File lock is already acquired.")

        if timeout is not None and timeout < 0:
            raise ValueError("Lock timeout cannot be negative.")

        deadline = (
            None if timeout is None else time.monotonic() + timeout
        )

        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Opening and registration must be atomic relative to fork handlers.
        # Otherwise a child could inherit an unregistered file descriptor.
        with _registry_guard:
            lock_file = self.path.open("a+b")
            self._file = lock_file
            _active_file_locks[id(self)] = self

        try:
            if os.name == "nt":
                self._acquire_windows(lock_file, deadline)
            else:
                self._acquire_unix(lock_file, deadline)

            return self

        except BaseException:
            with _registry_guard:
                try:
                    lock_file.close()
                finally:
                    self._file = None
                    _active_file_locks.pop(id(self), None)
            raise

    def _acquire_windows(self, lock_file, deadline: float | None) -> None:
        import msvcrt

        # Windows byte-range locks require a byte to exist.
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()

        lock_file.seek(0)

        while True:
            try:
                msvcrt.locking(
                    lock_file.fileno(),
                    msvcrt.LK_NBLCK,
                    1,
                )
                return
            except OSError as exc:
                if exc.errno not in (
                    errno.EACCES,
                    errno.EAGAIN,
                    errno.EDEADLK,
                    errno.EWOULDBLOCK,
                ):
                    raise

                self._wait_or_timeout(deadline)

    def _acquire_unix(self, lock_file, deadline: float | None) -> None:
        import fcntl

        if deadline is None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            return

        while True:
            try:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
                return
            except OSError as exc:
                if exc.errno not in (
                    errno.EACCES,
                    errno.EAGAIN,
                    errno.EWOULDBLOCK,
                ):
                    raise

                self._wait_or_timeout(deadline)

    def _wait_or_timeout(self, deadline: float | None) -> None:
        if deadline is None:
            time.sleep(_RETRY_INTERVAL_SECONDS)
            return

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FileLockTimeout(
                f"Timed out acquiring file lock: {self.path}"
            )

        time.sleep(min(_RETRY_INTERVAL_SECONDS, remaining))

    def release(self) -> None:
        """Release the operating-system lock and close its lock file."""

        with _registry_guard:
            lock_file = self._file
            if lock_file is None:
                return

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
                try:
                    lock_file.close()
                finally:
                    self._file = None
                    _active_file_locks.pop(id(self), None)

    def __enter__(self) -> Self:
        return self.acquire()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()


def create_file_lock(path: Path) -> CrossPlatformFileLock:
    """Return an unacquired process-safe lock for the specified path."""
    return CrossPlatformFileLock(path)


# Shared thread locks ensure that threads in this process coordinate before
# attempting the OS lock. The registry is shared by all repository consumers.
_registry_guard = threading.Lock()
_path_locks: dict[str, threading.RLock] = {}
_transaction_state = threading.local()

# Strong references are intentional: active lock objects must remain
# discoverable until their descriptors have been closed.
_active_file_locks: dict[int, CrossPlatformFileLock] = {}


def _before_fork() -> None:
    """Prevent registry mutation while the process is being forked."""
    _registry_guard.acquire()


def _after_fork_parent() -> None:
    """Release the registry guard in the parent after fork."""
    _registry_guard.release()


def _after_fork_child() -> None:
    """
    Close inherited descriptor copies and reset process-local lock state.

    Do not explicitly unlock inherited OS locks. On POSIX, flock ownership
    is associated with the open-file description and the parent must retain
    its lock until its own descriptor is released.
    """
    global _registry_guard
    global _path_locks
    global _transaction_state
    global _active_file_locks

    for lock in tuple(_active_file_locks.values()):
        inherited_file = lock._file
        lock._file = None

        if inherited_file is not None:
            try:
                inherited_file.close()
            except BaseException:
                # Fork cleanup must continue even if one descriptor fails.
                pass

    # These objects may contain mutex ownership belonging to threads that
    # do not exist in the child.
    _path_locks = {}
    _transaction_state = threading.local()
    _active_file_locks = {}
    _registry_guard = threading.Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(
        before=_before_fork,
        after_in_parent=_after_fork_parent,
        after_in_child=_after_fork_child,
    )


def _canonical_lock_path(path: Path) -> tuple[str, Path]:
    resolved = Path(path).resolve()
    key = os.path.normcase(str(resolved))
    return key, Path(key)


def _get_thread_lock(key: str) -> threading.RLock:
    with _registry_guard:
        lock = _path_locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _path_locks[key] = lock
        return lock


def _remaining_time(deadline: float | None) -> float | None:
    if deadline is None:
        return None
    return max(0.0, deadline - time.monotonic())


def _acquire_thread_lock(
    lock: threading.RLock,
    deadline: float | None,
    path: Path,
) -> None:
    remaining = _remaining_time(deadline)

    acquired = (
        lock.acquire()
        if remaining is None
        else lock.acquire(timeout=remaining)
    )

    if not acquired:
        raise FileLockTimeout(
            f"Timed out acquiring thread lock: {path}"
        )


@contextmanager
def file_lock_transaction(
    lock_path: Path,
    timeout: float | None = _DEFAULT_TRANSACTION_TIMEOUT_SECONDS,
) -> Iterator[None]:
    """
    Acquire a reentrant thread lock and an exclusive process lock.

    Nested transactions for the same canonical path and thread acquire the
    thread RLock again but reuse the outermost OS lock.

    The timeout is a total acquisition budget covering both lock layers.
    Pass None for an indefinite wait.

    Forking from the current thread while it holds an active transaction
    is unsupported. Forking from another thread is supported through
    the registered child-process cleanup handlers.
    """

    if timeout is not None and timeout < 0:
        raise ValueError("Lock timeout cannot be negative.")

    key, canonical_path = _canonical_lock_path(Path(lock_path))
    deadline = (
        None if timeout is None else time.monotonic() + timeout
    )

    owner_pid = os.getpid()

    thread_lock = _get_thread_lock(key)
    _acquire_thread_lock(thread_lock, deadline, canonical_path)

    state = getattr(_transaction_state, "locks", None)
    if state is None:
        state = {}
        _transaction_state.locks = state

    existing = state.get(key)

    if existing is not None:
        depth, os_lock = existing
        state[key] = (depth + 1, os_lock)

        try:
            yield
        finally:
            # The child fork handler has already closed inherited descriptor
            # copies and reset its registry. Never release the parent's lock
            # or inherited thread mutex from the child.
            if os.getpid() == owner_pid:
                current_depth, current_os_lock = state[key]
                state[key] = (current_depth - 1, current_os_lock)
                thread_lock.release()
        return

    os_lock = create_file_lock(canonical_path)

    try:
        os_lock.acquire(timeout=_remaining_time(deadline))
    except BaseException:
        thread_lock.release()
        raise

    state[key] = (1, os_lock)

    try:
        yield
    finally:
        if os.getpid() == owner_pid:
            del state[key]
            try:
                os_lock.release()
            finally:
                thread_lock.release()
