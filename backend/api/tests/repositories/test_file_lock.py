import multiprocessing
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.repositories import file_lock
from app.repositories.file_lock import create_file_lock


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
