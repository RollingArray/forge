import json
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import app.repositories.json_favorite_repository as favorite_repository_module

from app.interfaces.favorite import FavoriteResourceType
from app.repositories.json_favorite_repository import JsonFavoriteRepository


def test_users_have_separate_files_and_records(tmp_path: Path) -> None:
    repository = JsonFavoriteRepository(tmp_path)
    repository.create("user-a", FavoriteResourceType.DATA_MODEL, "model-1")
    repository.create("user-b", FavoriteResourceType.DATA_MODEL, "model-2")

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 2
    assert len(repository.get_by_user_id("user-a")) == 1
    assert len(repository.get_by_user_id("user-b")) == 1

    for path in files:
        document = json.loads(path.read_text(encoding="utf-8"))
        assert "user_id" not in document["favorites"][0]
        assert "user-a" not in path.name
        assert "user-b" not in path.name


def test_duplicate_favorite_returns_existing_record(tmp_path: Path) -> None:
    repository = JsonFavoriteRepository(tmp_path)

    first = repository.create(
        "user-a", FavoriteResourceType.DATA_MODEL, "model-1"
    )
    duplicate = repository.create(
        "user-a", FavoriteResourceType.DATA_MODEL, "model-1"
    )

    assert first.favorite_id == duplicate.favorite_id
    assert len(repository.get_by_user_id("user-a")) == 1


def test_delete_is_scoped_to_user_file(tmp_path: Path) -> None:
    repository = JsonFavoriteRepository(tmp_path)
    favorite = repository.create(
        "user-a", FavoriteResourceType.DATA_MODEL, "model-1"
    )

    assert repository.delete(favorite.favorite_id, "user-b") is False
    assert len(repository.get_by_user_id("user-a")) == 1
    assert repository.delete(favorite.favorite_id, "user-a") is True
    assert repository.get_by_user_id("user-a") == []


def test_favorites_survive_repository_restart(tmp_path: Path) -> None:
    first_repository = JsonFavoriteRepository(tmp_path)
    created = first_repository.create(
        "user-a", FavoriteResourceType.EXECUTION, "model-1", "job-1"
    )

    reloaded = JsonFavoriteRepository(tmp_path).get_by_user_id("user-a")

    assert len(reloaded) == 1
    assert reloaded[0].favorite_id == created.favorite_id
    assert reloaded[0].job_id == "job-1"


def test_concurrent_writes_preserve_same_users_favorites(
    tmp_path: Path,
) -> None:
    repository = JsonFavoriteRepository(tmp_path)

    def add(index: int) -> None:
        repository.create(
            "user-a",
            FavoriteResourceType.DATA_MODEL,
            f"model-{index}",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(add, range(40)))

    favorites = repository.get_by_user_id("user-a")
    assert len(favorites) == 40
    assert len({item.data_model_id for item in favorites}) == 40


def _create_favorites_in_process(
    root: str,
    process_number: int,
    favorite_count: int,
    duplicate: bool = False,
) -> None:
    repository = JsonFavoriteRepository(Path(root))

    for index in range(favorite_count):
        repository.create(
            "user-a",
            FavoriteResourceType.DATA_MODEL,
            "shared-model" if duplicate else (
                f"model-{process_number}-{index}"
            ),
        )


def test_independent_processes_preserve_same_users_favorites(
    tmp_path: Path,
) -> None:
    context = multiprocessing.get_context("spawn")

    processes = [
        context.Process(
            target=_create_favorites_in_process,
            args=(str(tmp_path), process_number, 20),
        )
        for process_number in range(4)
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join(timeout=30)

    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join()
            pytest.fail("Favorite writer process timed out.")

        assert process.exitcode == 0

    favorites = JsonFavoriteRepository(tmp_path).get_by_user_id("user-a")

    assert len(favorites) == 80
    assert len({item.favorite_id for item in favorites}) == 80
    assert len({item.data_model_id for item in favorites}) == 80


def test_concurrent_duplicate_creates_across_processes(
    tmp_path: Path,
) -> None:
    context = multiprocessing.get_context("spawn")

    processes = [
        context.Process(
            target=_create_favorites_in_process,
            args=(str(tmp_path), process_number, 10, True),
        )
        for process_number in range(4)
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join(timeout=30)

    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join()
            pytest.fail("Duplicate favorite writer process timed out.")

        assert process.exitcode == 0

    favorites = JsonFavoriteRepository(tmp_path).get_by_user_id("user-a")

    assert len(favorites) == 1
    assert favorites[0].data_model_id == "shared-model"


def test_failed_atomic_write_preserves_existing_favorites(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository = JsonFavoriteRepository(tmp_path)

    repository.create(
        "user-a",
        FavoriteResourceType.DATA_MODEL,
        "existing-model",
    )

    path = repository._path_for_user("user-a")
    original_content = path.read_bytes()

    def fail_atomic_write(*args, **kwargs):
        raise OSError("Simulated atomic write failure")

    monkeypatch.setattr(
        favorite_repository_module,
        "atomic_write_text",
        fail_atomic_write,
    )

    with pytest.raises(OSError, match="Simulated atomic write failure"):
        repository.create(
            "user-a",
            FavoriteResourceType.DATA_MODEL,
            "new-model",
        )

    assert path.read_bytes() == original_content

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert len(persisted["favorites"]) == 1
    assert persisted["favorites"][0]["data_model_id"] == "existing-model"

