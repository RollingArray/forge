from pathlib import Path
from threading import Event, Thread

import pytest

from app.repositories.file_lock import FileLockTimeout
from app.services.generation_execution_lease import (
    execution_lease_lock_path,
    generation_execution_lease,
)


def test_execution_lease_uses_stable_persistent_lock_file(tmp_path: Path):
    job_directory = tmp_path / "job"
    expected_path = (
        job_directory / ".locks" / "execution.lease.lock"
    )

    assert execution_lease_lock_path(job_directory) == expected_path

    with generation_execution_lease(job_directory):
        assert expected_path.is_file()

    assert expected_path.is_file()

    with generation_execution_lease(job_directory):
        assert expected_path.is_file()


def test_execution_lease_is_nonblocking_under_thread_contention(
    tmp_path: Path,
):
    job_directory = tmp_path / "job"
    acquired = Event()
    release = Event()
    failures = []

    def holder():
        try:
            with generation_execution_lease(job_directory):
                acquired.set()
                if not release.wait(timeout=5):
                    failures.append("Timed out waiting for test release.")
        except BaseException as exc:
            failures.append(exc)

    thread = Thread(target=holder)
    thread.start()

    try:
        assert acquired.wait(timeout=5)

        with pytest.raises(FileLockTimeout):
            with generation_execution_lease(job_directory, timeout=0):
                pytest.fail(
                    "A second execution lease was unexpectedly acquired."
                )
    finally:
        release.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert not failures


def test_execution_lease_releases_after_exception(tmp_path: Path):
    job_directory = tmp_path / "job"

    with pytest.raises(RuntimeError, match="simulated worker failure"):
        with generation_execution_lease(job_directory):
            raise RuntimeError("simulated worker failure")

    with generation_execution_lease(job_directory):
        pass


@pytest.mark.parametrize(
    "timeout",
    [-1, float("nan"), float("inf"), True],
)
def test_execution_lease_rejects_invalid_timeout(
    tmp_path: Path,
    timeout,
):
    with pytest.raises(ValueError, match="timeout"):
        with generation_execution_lease(
            tmp_path / "job",
            timeout=timeout,
        ):
            pass
