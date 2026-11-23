import json
import app.repositories.json_data_model_repository as data_model_repository_module
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)


def _repository_for_path(path: Path) -> JsonDataModelRepository:
    """Construct a repository using an isolated test store."""
    repository = JsonDataModelRepository.__new__(
        JsonDataModelRepository
    )
    repository._file_path = path
    return repository


def _create_models_in_process(
    path: str,
    process_number: int,
    model_count: int,
) -> None:
    """Create models from an independent process."""
    repository = _repository_for_path(Path(path))

    for index in range(model_count):
        repository.create(
            owner_user_id=f"user-{process_number}",
            name=f"Model {process_number}-{index}",
            description="Concurrent test",
            color="#7C5CFC",
            tags=["test"],
        )


def test_multiple_repository_instances_preserve_concurrent_creates(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "data_models.json"
    store_path.write_text(
        json.dumps({"data_models": []}),
        encoding="utf-8",
    )

    repositories = [
        _repository_for_path(store_path)
        for _ in range(8)
    ]

    def create(index: int) -> None:
        repositories[index % len(repositories)].create(
            owner_user_id="user-a",
            name=f"Model {index}",
            description="Concurrent test",
            color="#7C5CFC",
            tags=["test"],
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(create, range(100)))

    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    records = persisted["data_models"]

    assert len(records) == 100
    assert len({record["data_model_id"] for record in records}) == 100


def test_independent_processes_preserve_concurrent_creates(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "data_models.json"
    store_path.write_text(
        json.dumps({"data_models": []}),
        encoding="utf-8",
    )

    context = multiprocessing.get_context("spawn")
    process_count = 4
    models_per_process = 20

    processes = [
        context.Process(
            target=_create_models_in_process,
            args=(str(store_path), process_number, models_per_process),
        )
        for process_number in range(process_count)
    ]

    for process in processes:
        process.start()

    for process in processes:
        process.join(timeout=30)

    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join()
            raise AssertionError(
                "Data model writer process timed out."
            )

        assert process.exitcode == 0

    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    records = persisted["data_models"]

    assert len(records) == process_count * models_per_process
    assert len({record["data_model_id"] for record in records}) == len(records)


def test_concurrent_updates_preserve_all_records(tmp_path):
    path = tmp_path / "data_models.json"
    path.write_text(
        json.dumps({"data_models": []}),
        encoding="utf-8",
    )

    repository = _repository_for_path(path)
    owners = [f"user-{index}" for index in range(12)]

    models = [
        repository.create(
            owner_user_id=owner,
            name=f"Original {index}",
            description="Before update",
            color="#7C5CFC",
            tags=["original"],
        )
        for index, owner in enumerate(owners)
    ]

    def update_model(item):
        index, model = item
        repository_for_thread = _repository_for_path(path)

        repository_for_thread.update(
            model.data_model_id,
            owners[index],
            name=f"Updated {index}",
            description=f"Updated description {index}",
            color="#123456",
            tags=["updated", str(index)],
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(update_model, enumerate(models)))

    records = json.loads(path.read_text(encoding="utf-8"))["data_models"]

    assert len(records) == len(models)

    for index, owner in enumerate(owners):
        record = next(
            item for item in records
            if item["owner_user_id"] == owner
        )
        assert record["name"] == f"Updated {index}"
        assert record["description"] == f"Updated description {index}"


def test_concurrent_deletes_preserve_all_deletions(tmp_path):
    path = tmp_path / "data_models.json"
    path.write_text(
        json.dumps({"data_models": []}),
        encoding="utf-8",
    )

    repository = _repository_for_path(path)
    owners = [f"user-{index}" for index in range(16)]

    models = [
        repository.create(
            owner_user_id=owner,
            name=f"Model {index}",
            description="Delete concurrency test",
            color="#7C5CFC",
            tags=["delete-test"],
        )
        for index, owner in enumerate(owners)
    ]

    def delete_model(item):
        index, model = item
        repository_for_thread = _repository_for_path(path)
        return repository_for_thread.delete(
            model.data_model_id,
            owners[index],
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(delete_model, enumerate(models)))

    assert all(results)

    records = json.loads(path.read_text(encoding="utf-8"))["data_models"]
    assert records == []


def test_failed_atomic_write_preserves_existing_store(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "data_models.json"
    original_content = json.dumps(
        {"data_models": [{"id": "existing-record"}]},
        indent=2,
    ) + "\n"

    path.write_text(original_content, encoding="utf-8")

    repository = _repository_for_path(path)

    def fail_atomic_write(*args, **kwargs):
        raise OSError("Simulated atomic write failure")

    monkeypatch.setattr(
        data_model_repository_module,
        "atomic_write_text",
        fail_atomic_write,
    )

    import pytest

    with pytest.raises(OSError, match="Simulated atomic write failure"):
        repository.create(
            owner_user_id="failure-test-user",
            name="Should not be persisted",
            description="Atomic failure test",
            color="#7C5CFC",
            tags=["failure-test"],
        )

    assert path.read_text(encoding="utf-8") == original_content

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["data_models"] == [
        {"id": "existing-record"}
    ]

