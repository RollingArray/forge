import json
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import app.repositories.json_data_model_access_repository as access_repository_module
from app.constants.data_model_access import DataModelAccessRole
from app.repositories.json_data_model_access_repository import (
    JsonDataModelAccessRepository,
)


def _repository_for_path(path):
    repository = JsonDataModelAccessRepository.__new__(
        JsonDataModelAccessRepository
    )
    repository._file_path = path
    return repository


def _grant_access_in_process(path, process_number, grant_count):
    repository = _repository_for_path(Path(path))

    for index in range(grant_count):
        repository.grant_access(
            data_model_id=f"model-{process_number}-{index}",
            user_id=f"user-{process_number}-{index}",
            role=DataModelAccessRole.CONTRIBUTOR,
        )


def test_concurrent_grants_preserve_all_records_across_instances(tmp_path):
    path = tmp_path / "data_model_access.json"
    path.write_text(
        json.dumps({"access": []}),
        encoding="utf-8",
    )

    def grant(item):
        index = item
        repository = _repository_for_path(path)
        repository.grant_access(
            data_model_id=f"model-{index}",
            user_id=f"user-{index}",
            role=DataModelAccessRole.CONTRIBUTOR,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(grant, range(100)))

    records = json.loads(path.read_text(encoding="utf-8"))["access"]

    assert len(records) == 100
    assert len({
        (record["data_model_id"], record["user_id"])
        for record in records
    }) == 100


def test_independent_processes_preserve_concurrent_grants(tmp_path):
    path = tmp_path / "data_model_access.json"
    path.write_text(
        json.dumps({"access": []}),
        encoding="utf-8",
    )

    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(
            target=_grant_access_in_process,
            args=(str(path), process_number, 20),
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
            pytest.fail("Access writer process timed out.")

        assert process.exitcode == 0

    records = json.loads(path.read_text(encoding="utf-8"))["access"]

    assert len(records) == 80
    assert len({
        (record["data_model_id"], record["user_id"])
        for record in records
    }) == 80


def test_regrant_updates_role_without_replacing_grant_identity(tmp_path):
    path = tmp_path / "data_model_access.json"
    path.write_text(
        json.dumps({"access": []}),
        encoding="utf-8",
    )

    repository = _repository_for_path(path)

    original = repository.grant_access(
        "model-1",
        "user-1",
        DataModelAccessRole.CONTRIBUTOR,
    )

    original_record = json.loads(
        path.read_text(encoding="utf-8")
    )["access"][0]

    updated = repository.grant_access(
        "model-1",
        "user-1",
        DataModelAccessRole.VIEWER,
    )

    updated_records = json.loads(
        path.read_text(encoding="utf-8")
    )["access"]

    assert len(updated_records) == 1
    assert updated_records[0]["access_id"] == original_record["access_id"]
    assert updated_records[0]["granted_at"] == original_record["granted_at"]
    assert updated.role == DataModelAccessRole.VIEWER
    assert updated.granted_at == original.granted_at


def test_update_role_and_revoke_preserve_repository_contract(tmp_path):
    path = tmp_path / "data_model_access.json"
    path.write_text(
        json.dumps({"access": []}),
        encoding="utf-8",
    )

    repository = _repository_for_path(path)

    assert repository.update_role(
        "model-missing",
        "user-missing",
        DataModelAccessRole.VIEWER,
    ) is None

    assert repository.revoke_access(
        "model-missing",
        "user-missing",
    ) is False

    repository.grant_access(
        "model-1",
        "user-1",
        DataModelAccessRole.CONTRIBUTOR,
    )

    updated = repository.update_role(
        "model-1",
        "user-1",
        DataModelAccessRole.VIEWER,
    )

    assert updated is not None
    assert updated.role == DataModelAccessRole.VIEWER

    assert repository.revoke_access("model-1", "user-1") is True
    assert repository.revoke_access("model-1", "user-1") is False
    assert repository.get_access("model-1", "user-1") is None


def test_failed_atomic_write_preserves_existing_access_store(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "data_model_access.json"
    original_content = json.dumps(
        {"access": []},
        indent=2,
    ) + "\n"

    path.write_text(original_content, encoding="utf-8")

    repository = _repository_for_path(path)

    def fail_atomic_write(*args, **kwargs):
        raise OSError("Simulated atomic write failure")

    monkeypatch.setattr(
        access_repository_module,
        "atomic_write_text",
        fail_atomic_write,
    )

    with pytest.raises(OSError, match="Simulated atomic write failure"):
        repository.grant_access(
            "model-1",
            "user-1",
            DataModelAccessRole.CONTRIBUTOR,
        )

    assert path.read_text(encoding="utf-8") == original_content
    assert json.loads(path.read_text(encoding="utf-8")) == {"access": []}
