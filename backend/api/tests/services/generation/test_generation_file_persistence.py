import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import generation_file_persistence as persistence


def test_generation_file_lock_serializes_threads(
    tmp_path: Path,
) -> None:
    path = tmp_path / "state.json"
    counter = {"value": 0}

    def increment() -> None:
        for _ in range(50):
            with persistence.generation_file_lock(path):
                current = counter["value"]
                counter["value"] = current + 1

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: increment(), range(8)))

    assert counter["value"] == 400


def test_atomic_write_replaces_destination_and_cleans_temporary_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "state.json"
    path.write_text("old", encoding="utf-8")

    persistence.atomic_write_text(path, "new")

    assert path.read_text(encoding="utf-8") == "new"
    assert list(tmp_path.glob(".state.json.*.tmp")) == []


def test_atomic_write_preserves_destination_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state.json"
    path.write_text("original", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise PermissionError("access denied")

    monkeypatch.setattr(
        persistence.os,
        "replace",
        fail_replace,
    )

    with pytest.raises(PermissionError, match="access denied"):
        persistence.atomic_write_text(path, "replacement")

    assert path.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.glob(".state.json.*.tmp")) == []


def test_atomic_write_retries_windows_sharing_violation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state.json"
    real_os = os
    attempts = []

    def replace_with_transient_failure(
        source: Path,
        destination: Path,
    ) -> None:
        attempts.append(1)

        if len(attempts) == 1:
            error = OSError("sharing violation")
            error.winerror = 32
            raise error

        real_os.replace(source, destination)

    fake_os = SimpleNamespace(
        name="nt",
        fdopen=real_os.fdopen,
        fsync=real_os.fsync,
        replace=replace_with_transient_failure,
    )

    monkeypatch.setattr(
        persistence,
        "os",
        fake_os,
    )
    monkeypatch.setattr(
        persistence.time,
        "sleep",
        lambda _: None,
    )

    persistence.atomic_write_text(path, "saved")

    assert len(attempts) == 2
    assert path.read_text(encoding="utf-8") == "saved"
    assert list(tmp_path.glob(".state.json.*.tmp")) == []


def test_atomic_write_does_not_retry_access_denied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state.json"
    path.write_text("original", encoding="utf-8")
    attempts = []

    def fail_with_access_denied(
        source: Path,
        destination: Path,
    ) -> None:
        attempts.append(1)
        error = PermissionError("access denied")
        error.winerror = 5
        raise error

    fake_os = SimpleNamespace(
        name="nt",
        fdopen=os.fdopen,
        fsync=os.fsync,
        replace=fail_with_access_denied,
    )

    monkeypatch.setattr(
        persistence,
        "os",
        fake_os,
    )

    with pytest.raises(PermissionError, match="access denied"):
        persistence.atomic_write_text(path, "replacement")

    assert len(attempts) == 1
    assert path.read_text(encoding="utf-8") == "original"
    assert list(tmp_path.glob(".state.json.*.tmp")) == []
