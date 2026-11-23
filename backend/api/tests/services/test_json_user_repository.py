import json
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import app.services.json_user_repository as user_repository_module
from app.services.json_user_repository import JsonUserRepository


def _repository_for_path(path):
    repository = JsonUserRepository.__new__(JsonUserRepository)
    repository._file_path = path
    return repository


def _create_users_in_process(path, process_number, user_count):
    repository = _repository_for_path(Path(path))

    for index in range(user_count):
        repository.create(
            email=f"user-{process_number}-{index}@example.com",
            display_name=f"User {process_number}-{index}",
        )


def test_concurrent_creates_preserve_all_users_across_instances(tmp_path):
    path = tmp_path / "users.json"
    path.write_text(json.dumps({"users": []}), encoding="utf-8")

    def create_user(index):
        repository = _repository_for_path(path)
        return repository.create(
            email=f"user-{index}@example.com",
            display_name=f"User {index}",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        users = list(executor.map(create_user, range(100)))

    records = json.loads(path.read_text(encoding="utf-8"))["users"]

    assert len(records) == 100
    assert len({record["user_id"] for record in records}) == 100
    assert len({record["email"] for record in records}) == 100
    assert len({user.user_id for user in users}) == 100


def test_independent_processes_preserve_concurrent_user_creates(tmp_path):
    path = tmp_path / "users.json"
    path.write_text(json.dumps({"users": []}), encoding="utf-8")

    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(
            target=_create_users_in_process,
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
            pytest.fail("User writer process timed out.")

        assert process.exitcode == 0

    records = json.loads(path.read_text(encoding="utf-8"))["users"]

    assert len(records) == 80
    assert len({record["user_id"] for record in records}) == 80
    assert len({record["email"] for record in records}) == 80


def test_concurrent_duplicate_email_creates_return_one_user(tmp_path):
    path = tmp_path / "users.json"
    path.write_text(json.dumps({"users": []}), encoding="utf-8")

    def create_duplicate(index):
        repository = _repository_for_path(path)
        return repository.create(
            email="  Shared.User@Example.com  ",
            display_name=f"Attempt {index}",
        )

    with ThreadPoolExecutor(max_workers=12) as executor:
        users = list(executor.map(create_duplicate, range(40)))

    records = json.loads(path.read_text(encoding="utf-8"))["users"]

    assert len(records) == 1
    assert records[0]["email"] == "shared.user@example.com"
    assert len({user.user_id for user in users}) == 1
    assert all(
        user.user_id == records[0]["user_id"]
        for user in users
    )


def test_profile_update_preserves_stable_forge_user_id(tmp_path):
    path = tmp_path / "users.json"
    path.write_text(json.dumps({"users": []}), encoding="utf-8")

    repository = _repository_for_path(path)

    original = repository.create(
        email="person@example.com",
        display_name="Original Name",
    )

    profile = {
        "userId": "employee-123",
        "fullName": "Updated Name",
        "email": "person@example.com",
    }

    updated = repository.update_profile(
        "PERSON@example.com",
        profile,
    )

    records = json.loads(path.read_text(encoding="utf-8"))["users"]

    assert len(records) == 1
    assert updated.user_id == original.user_id
    assert updated.display_name == "Updated Name"
    assert updated.employee_id == "employee-123"
    assert updated.profile == profile
    assert records[0]["user_id"] == original.user_id


def test_email_lookup_search_and_missing_profile_contract(tmp_path):
    path = tmp_path / "users.json"
    path.write_text(json.dumps({"users": []}), encoding="utf-8")

    repository = _repository_for_path(path)

    user = repository.create(
        email="  Example.User@Example.com ",
        display_name="Example User",
    )

    assert repository.get_by_email(
        "EXAMPLE.USER@example.com"
    ).user_id == user.user_id

    assert repository.get_by_id(
        user.user_id
    ).email == "example.user@example.com"

    assert repository.get_by_id("  ") is None
    assert repository.get_by_email("missing@example.com") is None

    assert len(repository.search("EXAMPLE")) == 1
    assert repository.search("  ") == []
    assert repository.search("example", limit=0)

    with pytest.raises(ValueError, match="must exist"):
        repository.update_profile(
            "missing@example.com",
            {
                "userId": "employee-999",
                "fullName": "Missing User",
            },
        )


def test_failed_atomic_write_preserves_existing_user_store(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "users.json"
    original_content = json.dumps(
        {"users": []},
        indent=2,
    ) + "\n"

    path.write_text(original_content, encoding="utf-8")

    repository = _repository_for_path(path)

    def fail_atomic_write(*args, **kwargs):
        raise OSError("Simulated atomic write failure")

    monkeypatch.setattr(
        user_repository_module,
        "atomic_write_text",
        fail_atomic_write,
    )

    with pytest.raises(OSError, match="Simulated atomic write failure"):
        repository.create(
            email="failure@example.com",
            display_name="Failure Test",
        )

    assert path.read_text(encoding="utf-8") == original_content
    assert json.loads(path.read_text(encoding="utf-8")) == {"users": []}
