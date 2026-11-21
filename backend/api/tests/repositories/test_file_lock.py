import multiprocessing
import os
import sys
import threading
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.repositories import file_lock
from app.repositories.file_lock import create_file_lock


def _hold_file_lock(
    lock_path: str,
    ready,
    release,
) -> None:
    """Hold an OS file lock until the parent process releases it."""
    with create_file_lock(Path(lock_path)):
        ready.set()
        release.wait(timeout=10)


def _increment_counter(
    lock_path: str,
    counter_path: str,
    iterations: int,
) -> None:
    """Increment a shared counter while holding the process-level lock."""
    lock = create_file_lock(Path(lock_path))
    counter = Path(counter_path)

    for _ in range(iterations):
        with lock:
            value = int(counter.read_text()) if counter.exists() else 0
            counter.write_text(str(value + 1))


def test_file_lock_acquires_releases_and_can_be_reacquired(
    tmp_path: Path,
) -> None:
    lock = create_file_lock(tmp_path / "test.lock")

    with lock:
        assert lock._file is not None

    assert lock._file is None

    with lock:
        assert lock._file is not None

    assert lock._file is None


def test_file_lock_rejects_double_acquisition(
    tmp_path: Path,
) -> None:
    lock = create_file_lock(tmp_path / "test.lock")

    with lock:
        with pytest.raises(RuntimeError, match="already acquired"):
            lock.acquire()


def test_windows_locking_branch_uses_msvcrt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operations = []

    fake_msvcrt = types.ModuleType("msvcrt")
    fake_msvcrt.LK_NBLCK = 1
    fake_msvcrt.LK_UNLCK = 2
    fake_msvcrt.locking = lambda descriptor, mode, count: (
        operations.append((mode, count))
    )

    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(
        file_lock,
        "os",
        SimpleNamespace(name="nt", SEEK_END=os.SEEK_END),
    )

    lock_path = tmp_path / "windows.lock"
    lock = create_file_lock(lock_path)

    with lock:
        assert lock._file is not None
        assert lock_path.stat().st_size == 1

    assert operations == [
        (fake_msvcrt.LK_NBLCK, 1),
        (fake_msvcrt.LK_UNLCK, 1),
    ]
    assert lock._file is None


def test_file_lock_serializes_concurrent_processes(
    tmp_path: Path,
) -> None:
    process_count = 4
    increments_per_process = 20

    lock_path = tmp_path / "counter.lock"
    counter_path = tmp_path / "counter.txt"

    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(
            target=_increment_counter,
            args=(
                str(lock_path),
                str(counter_path),
                increments_per_process,
            ),
        )
        for _ in range(process_count)
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join(timeout=30)

    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join()
            raise AssertionError("File-lock writer process timed out.")

        assert process.exitcode == 0

    assert int(counter_path.read_text()) == (
        process_count * increments_per_process
    )


def test_file_lock_transaction_nested_acquisition_uses_one_os_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acquisitions = []
    releases = []
    real_factory = file_lock.create_file_lock

    class CountingLock:
        def __init__(self, path: Path) -> None:
            self.lock = real_factory(path)

        def acquire(self, timeout=None):
            acquisitions.append(timeout)
            self.lock.acquire(timeout=timeout)
            return self

        def release(self):
            releases.append(True)
            self.lock.release()

    monkeypatch.setattr(file_lock, "create_file_lock", CountingLock)

    lock_path = tmp_path / "nested.lock"

    with file_lock.file_lock_transaction(lock_path):
        with file_lock.file_lock_transaction(lock_path):
            with file_lock.file_lock_transaction(lock_path):
                assert len(acquisitions) == 1
                assert len(releases) == 0

    assert len(acquisitions) == 1
    assert len(releases) == 1


def test_file_lock_transaction_releases_after_exception(
    tmp_path: Path,
) -> None:
    lock_path = tmp_path / "exception.lock"

    with pytest.raises(ValueError, match="expected failure"):
        with file_lock.file_lock_transaction(lock_path):
            raise ValueError("expected failure")

    with file_lock.file_lock_transaction(lock_path):
        pass


def test_file_lock_transaction_times_out_on_thread_contention(
    tmp_path: Path,
) -> None:
    lock_path = tmp_path / "thread-contention.lock"
    results = []

    def competing_thread() -> None:
        try:
            with file_lock.file_lock_transaction(lock_path, timeout=0.15):
                results.append("acquired")
        except file_lock.FileLockTimeout:
            results.append("timed_out")

    with file_lock.file_lock_transaction(lock_path):
        worker = threading.Thread(target=competing_thread)
        worker.start()
        worker.join(timeout=2)
        assert not worker.is_alive()

    assert results == ["timed_out"]


def test_file_lock_transactions_on_independent_paths_do_not_conflict(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.lock"
    second_path = tmp_path / "second.lock"

    with file_lock.file_lock_transaction(first_path):
        with file_lock.file_lock_transaction(second_path):
            pass

    with file_lock.file_lock_transaction(first_path):
        with file_lock.file_lock_transaction(second_path):
            pass



def test_file_lock_transaction_times_out_on_process_contention(
    tmp_path: Path,
) -> None:
    context = multiprocessing.get_context("spawn")
    lock_path = tmp_path / "process-contention.lock"
    ready = context.Event()
    release = context.Event()

    process = context.Process(
        target=_hold_file_lock,
        args=(str(lock_path), ready, release),
    )
    process.start()

    try:
        assert ready.wait(timeout=5), "Child process did not acquire the lock."

        with pytest.raises(file_lock.FileLockTimeout):
            with file_lock.file_lock_transaction(
                lock_path,
                timeout=0.2,
            ):
                pass
    finally:
        release.set()
        process.join(timeout=10)

        if process.is_alive():
            process.terminate()
            process.join()
            raise AssertionError("Lock-holder process did not exit.")

    assert process.exitcode == 0


def _fork_child_acquire_transaction(
    lock_path: str,
    result_fd: int,
) -> None:
    """Attempt a fresh transaction in a forked child process."""
    try:
        with file_lock.file_lock_transaction(
            Path(lock_path),
            timeout=0.2,
        ):
            result = b"unexpected-acquisition"
    except file_lock.FileLockTimeout as exc:
        message = str(exc)
        if "Timed out acquiring file lock:" in message:
            result = b"os-lock-blocked"
        elif "Timed out acquiring thread lock:" in message:
            result = b"thread-lock-stale"
        else:
            result = f"unexpected-timeout: {message}".encode()
    except BaseException as exc:
        result = f"unexpected-error: {exc}".encode(
            "utf-8",
            errors="replace",
        )

    try:
        os.write(result_fd, result)
    finally:
        os.close(result_fd)


@pytest.mark.skipif(
    not hasattr(os, "fork"),
    reason="Fork is not available on this platform.",
)
def test_fork_child_reaches_os_lock_when_parent_thread_holds_transaction(
    tmp_path: Path,
) -> None:
    """A child must not inherit a vanished thread's active transaction."""
    lock_path = tmp_path / "fork-inherited.lock"

    lock_acquired = threading.Event()
    release_lock = threading.Event()

    def hold_parent_transaction() -> None:
        with file_lock.file_lock_transaction(lock_path):
            lock_acquired.set()
            release_lock.wait(timeout=10)

    worker = threading.Thread(target=hold_parent_transaction)
    worker.start()

    read_fd, write_fd = os.pipe()
    child_pid = None

    try:
        assert lock_acquired.wait(timeout=5), (
            "Parent worker did not acquire the transaction lock."
        )

        child_pid = os.fork()

        if child_pid == 0:
            os.close(read_fd)
            _fork_child_acquire_transaction(
                str(lock_path),
                write_fd,
            )
            os._exit(0)

        os.close(write_fd)
        write_fd = -1

        result = os.read(read_fd, 1024)
        _, status = os.waitpid(child_pid, 0)
        child_pid = None

        assert os.waitstatus_to_exitcode(status) == 0
        assert result == b"os-lock-blocked", result.decode(
            "utf-8",
            errors="replace",
        )

    finally:
        os.close(read_fd)

        if write_fd >= 0:
            os.close(write_fd)

        if child_pid is not None:
            os.kill(child_pid, 9)
            os.waitpid(child_pid, 0)

        release_lock.set()
        worker.join(timeout=5)

    assert not worker.is_alive()


def _fork_child_verify_lock_lifecycle(
    lock_path: str,
    command_fd: int,
    result_fd: int,
) -> None:
    """Verify inherited lock contention and subsequent acquisition."""
    try:
        try:
            with file_lock.file_lock_transaction(
                Path(lock_path),
                timeout=0.2,
            ):
                first_result = b"unexpected-acquisition"
        except file_lock.FileLockTimeout as exc:
            if "Timed out acquiring file lock:" in str(exc):
                first_result = b"os-lock-blocked"
            else:
                first_result = b"thread-lock-stale"

        os.write(result_fd, first_result + b"\n")

        command = os.read(command_fd, 1)
        if command != b"g":
            os.write(result_fd, b"invalid-command\n")
            return

        with file_lock.file_lock_transaction(
            Path(lock_path),
            timeout=2.0,
        ):
            os.write(result_fd, b"acquired-after-parent-release\n")

    except BaseException as exc:
        message = str(exc).encode("utf-8", errors="replace")
        os.write(result_fd, b"error:" + message + b"\n")

    finally:
        os.close(command_fd)
        os.close(result_fd)


@pytest.mark.skipif(
    not hasattr(os, "fork"),
    reason="Fork is not available on this platform.",
)
def test_fork_child_acquires_lock_after_parent_releases_transaction(
    tmp_path: Path,
) -> None:
    """Child cleanup must preserve the parent lock and permit later reuse."""
    lock_path = tmp_path / "fork-lifecycle.lock"

    lock_acquired = threading.Event()
    release_lock = threading.Event()

    def hold_parent_transaction() -> None:
        with file_lock.file_lock_transaction(lock_path):
            lock_acquired.set()
            release_lock.wait(timeout=10)

    worker = threading.Thread(target=hold_parent_transaction)
    worker.start()

    child_result_read, child_result_write = os.pipe()
    parent_command_read, parent_command_write = os.pipe()
    child_pid = None

    try:
        assert lock_acquired.wait(timeout=5), (
            "Parent worker did not acquire the transaction lock."
        )

        child_pid = os.fork()

        if child_pid == 0:
            os.close(child_result_read)
            os.close(parent_command_write)

            _fork_child_verify_lock_lifecycle(
                str(lock_path),
                parent_command_read,
                child_result_write,
            )
            os._exit(0)

        os.close(child_result_write)
        child_result_write = -1
        os.close(parent_command_read)
        parent_command_read = -1

        first_result = os.read(child_result_read, 1024).strip()
        assert first_result == b"os-lock-blocked", (
            f"Expected OS-level contention, got: {first_result!r}"
        )

        # The child has closed its inherited descriptor copy. The parent
        # must still own the lock until its original transaction exits.
        release_lock.set()
        worker.join(timeout=5)

        assert not worker.is_alive(), (
            "Parent transaction did not release its lock."
        )

        os.write(parent_command_write, b"g")

        second_result = os.read(child_result_read, 1024).strip()
        assert second_result == b"acquired-after-parent-release", (
            f"Child could not acquire the released lock: {second_result!r}"
        )

        _, status = os.waitpid(child_pid, 0)
        child_pid = None

        assert os.waitstatus_to_exitcode(status) == 0

    finally:
        release_lock.set()
        worker.join(timeout=5)

        for fd in (
            child_result_read,
            child_result_write,
            parent_command_read,
            parent_command_write,
        ):
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass

        if child_pid is not None:
            os.kill(child_pid, 9)
            os.waitpid(child_pid, 0)

    assert not worker.is_alive()



def _hold_file_lock_until_terminated(
    lock_path: str,
    ready,
) -> None:
    """Hold an OS lock until the parent forcibly terminates this process."""
    import time

    with create_file_lock(Path(lock_path)):
        ready.set()

        while True:
            time.sleep(1)


def test_file_lock_is_released_after_process_termination(
    tmp_path: Path,
) -> None:
    """The OS must release a process lock when its owner is terminated."""
    context = multiprocessing.get_context("spawn")
    lock_path = tmp_path / "terminated-process.lock"

    ready = context.Event()

    process = context.Process(
        target=_hold_file_lock_until_terminated,
        args=(str(lock_path), ready),
    )
    process.start()

    try:
        assert ready.wait(timeout=5), (
            "Child process did not acquire the file lock."
        )

        # Terminate without allowing the worker's context manager to exit.
        process.terminate()
        process.join(timeout=5)

        assert not process.is_alive(), (
            "Lock-holder process did not terminate."
        )
        assert process.exitcode is not None
        assert process.exitcode != 0

        # The OS must release the abandoned lock.
        with file_lock.file_lock_transaction(
            lock_path,
            timeout=2.0,
        ):
            pass

    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
