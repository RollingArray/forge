import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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
