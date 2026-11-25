import json

from app.repositories.json_specification_repository import (
    JsonSpecificationRepository,
)


def test_decimal_strings_survive_specification_save_and_reload(
    tmp_path,
    monkeypatch,
):
    repository = JsonSpecificationRepository()
    monkeypatch.setattr(repository, "_data_directory", tmp_path)

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "fields": [
                    {
                        "name": "PRICE",
                        "type": "DECIMAL",
                        "generation": {
                            "min": "0.1000",
                            "max": "999999999999999999.123400",
                        },
                    }
                ],
            }
        ]
    }

    repository.save("MODEL-DECIMAL", specification)
    reloaded = repository.read("MODEL-DECIMAL")

    assert reloaded == specification

    persisted = json.loads(
        (
            tmp_path
            / "data_model"
            / "MODEL-DECIMAL"
            / "specification.json"
        ).read_text(encoding="utf-8")
    )

    generation = persisted["entities"][0]["fields"][0]["generation"]
    assert generation["min"] == "0.1000"
    assert generation["max"] == "999999999999999999.123400"


def test_specification_revision_distinguishes_decimal_representation():
    base = {
        "entities": [
            {
                "fields": [
                    {
                        "name": "PRICE",
                        "type": "DECIMAL",
                        "generation": {"min": "0.1"},
                    }
                ]
            }
        ]
    }
    with_trailing_zeros = {
        "entities": [
            {
                "fields": [
                    {
                        "name": "PRICE",
                        "type": "DECIMAL",
                        "generation": {"min": "0.1000"},
                    }
                ]
            }
        ]
    }

    assert (
        JsonSpecificationRepository.revision(base)
        != JsonSpecificationRepository.revision(with_trailing_zeros)
    )


def test_nested_transactions_acquire_and_release_file_lock_once(
    tmp_path,
    monkeypatch,
):
    import app.repositories.file_lock as file_lock_module

    repository = JsonSpecificationRepository()
    monkeypatch.setattr(repository, "_data_directory", tmp_path)

    class TrackingLock:
        def __init__(self, path):
            self.path = path
            self.acquire_count = 0
            self.release_count = 0

        def acquire(self, timeout=None):
            self.acquire_count += 1
            return self

        def release(self):
            self.release_count += 1

    tracking_lock = TrackingLock(tmp_path / "tracked.lock")
    factory_calls = []

    def create_tracking_lock(path):
        factory_calls.append(path)
        return tracking_lock

    monkeypatch.setattr(
        file_lock_module,
        "create_file_lock",
        create_tracking_lock,
    )

    with repository.transaction("MODEL-NESTED"):
        assert tracking_lock.acquire_count == 1
        assert tracking_lock.release_count == 0

        with repository.transaction("MODEL-NESTED"):
            assert tracking_lock.acquire_count == 1
            assert tracking_lock.release_count == 0

        assert tracking_lock.acquire_count == 1
        assert tracking_lock.release_count == 0

    assert tracking_lock.acquire_count == 1
    assert tracking_lock.release_count == 1
    assert len(factory_calls) == 1


def test_delete_removes_specification_and_empty_model_directory(
    tmp_path,
    monkeypatch,
):
    repository = JsonSpecificationRepository()
    monkeypatch.setattr(repository, "_data_directory", tmp_path)

    repository.save(
        "MODEL-DELETE",
        {"model": {"name": "Temporary copy"}},
    )

    model_directory = tmp_path / "data_model" / "MODEL-DELETE"
    assert (model_directory / "specification.json").exists()

    assert repository.delete("MODEL-DELETE") is True
    assert not (model_directory / "specification.json").exists()
    assert not model_directory.exists()


def test_delete_preserves_unrelated_files_in_model_directory(
    tmp_path,
    monkeypatch,
):
    repository = JsonSpecificationRepository()
    monkeypatch.setattr(repository, "_data_directory", tmp_path)

    repository.save(
        "MODEL-PRESERVE",
        {"model": {"name": "Temporary copy"}},
    )

    model_directory = tmp_path / "data_model" / "MODEL-PRESERVE"
    unrelated_file = model_directory / "unrelated.json"
    unrelated_file.write_text('{"preserve": true}', encoding="utf-8")

    assert repository.delete("MODEL-PRESERVE") is True

    assert not (model_directory / "specification.json").exists()
    assert unrelated_file.exists()
    assert unrelated_file.read_text(encoding="utf-8") == (
        '{"preserve": true}'
    )


def test_delete_is_safe_when_specification_does_not_exist(
    tmp_path,
    monkeypatch,
):
    repository = JsonSpecificationRepository()
    monkeypatch.setattr(repository, "_data_directory", tmp_path)

    assert repository.delete("MODEL-MISSING") is False
