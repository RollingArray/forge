from multiprocessing import get_context
from pathlib import Path
from threading import Event, Thread

import pytest

from app.repositories.file_lock import FileLockTimeout
from app.services.generation_job_transition import (
    generation_job_transition_lock,
    lifecycle_transition_lock_path,
)


def _hold_transition_lock(
    job_directory: str,
    acquired,
    release,
) -> None:
    with generation_job_transition_lock(Path(job_directory), timeout=5):
        acquired.set()
        if not release.wait(timeout=10):
            raise RuntimeError("Timed out waiting for test release.")


def test_transition_lock_uses_stable_persistent_file(
    tmp_path: Path,
) -> None:
    job_directory = tmp_path / "job"
    expected = (
        job_directory / ".locks" / "lifecycle.transition.lock"
    )

    assert lifecycle_transition_lock_path(job_directory) == expected

    with generation_job_transition_lock(job_directory):
        assert expected.is_file()

    assert expected.is_file()

    with generation_job_transition_lock(job_directory):
        assert expected.is_file()


def test_transition_lock_releases_after_exception(
    tmp_path: Path,
) -> None:
    with pytest.raises(RuntimeError, match="simulated failure"):
        with generation_job_transition_lock(tmp_path / "job"):
            raise RuntimeError("simulated failure")

    with generation_job_transition_lock(tmp_path / "job"):
        pass


@pytest.mark.parametrize(
    "timeout",
    [-1, float("nan"), float("inf"), True],
)
def test_transition_lock_rejects_invalid_timeout(
    tmp_path: Path,
    timeout,
) -> None:
    with pytest.raises(ValueError, match="timeout"):
        with generation_job_transition_lock(
            tmp_path / "job",
            timeout=timeout,
        ):
            pass


def test_transition_lock_serializes_independent_processes(
    tmp_path: Path,
) -> None:
    context = get_context("spawn")
    job_directory = tmp_path / "job"
    acquired = context.Event()
    release = context.Event()

    process = context.Process(
        target=_hold_transition_lock,
        args=(str(job_directory), acquired, release),
    )
    process.start()

    try:
        assert acquired.wait(timeout=10)

        with pytest.raises(FileLockTimeout):
            with generation_job_transition_lock(
                job_directory,
                timeout=0,
            ):
                pytest.fail(
                    "A second process unexpectedly acquired the lock."
                )
    finally:
        release.set()
        process.join(timeout=10)

        if process.is_alive():
            process.terminate()
            process.join(timeout=5)

    assert process.exitcode == 0


def test_transition_lock_serializes_threads(
    tmp_path: Path,
) -> None:
    job_directory = tmp_path / "job"
    acquired = Event()
    release = Event()
    failures = []

    def holder() -> None:
        try:
            with generation_job_transition_lock(job_directory):
                acquired.set()
                if not release.wait(timeout=5):
                    failures.append("Timed out waiting for release.")
        except BaseException as exc:
            failures.append(exc)

    thread = Thread(target=holder)
    thread.start()

    try:
        assert acquired.wait(timeout=5)

        with pytest.raises(FileLockTimeout):
            with generation_job_transition_lock(
                job_directory,
                timeout=0,
            ):
                pytest.fail("A second thread unexpectedly acquired the lock.")
    finally:
        release.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert not failures
