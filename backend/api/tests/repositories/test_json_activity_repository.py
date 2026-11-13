import json
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.repositories.json_activity_repository import JsonActivityRepository


OWNER_ID = "owner-test"
ACTOR_ID = "actor-test"


def build_repository(data_directory: Path) -> JsonActivityRepository:
    repository = JsonActivityRepository()
    repository._data_directory = data_directory
    repository._lock_directory = data_directory / ".locks"
    return repository


def create_activity(
    repository: JsonActivityRepository,
    title: str,
    *,
    owner_user_id: str = OWNER_ID,
    data_model_id: str | None = None,
    metadata: dict | None = None,
):
    return repository.create(
        owner_user_id=owner_user_id,
        actor_user_id=ACTOR_ID,
        activity_type="MODEL_CREATED",
        title=title,
        description=f"Description for {title}",
        data_model_id=data_model_id,
        job_id=f"job-{title}",
        metadata=metadata or {},
    )


def _write_activities_in_process(
    data_directory: str,
    process_number: int,
    count: int,
) -> None:
    repository = build_repository(Path(data_directory))

    for index in range(count):
        create_activity(
            repository,
            title=f"process-{process_number}-activity-{index}",
        )


def test_create_and_retrieve_activity_preserves_all_fields(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    created = repository.create(
        owner_user_id=OWNER_ID,
        actor_user_id=ACTOR_ID,
        activity_type="MODEL_CREATED",
        title="  Model created  ",
        description="  Initial model creation  ",
        data_model_id="model-1",
        job_id="job-1",
        metadata={"source": "test", "details": {"version": 1}},
    )

    activities = repository.get_by_data_model_id("model-1")

    assert len(activities) == 1

    retrieved = activities[0]
    assert retrieved.activity_id == created.activity_id
    assert retrieved.owner_user_id == OWNER_ID
    assert retrieved.actor_user_id == ACTOR_ID
    assert retrieved.type == "MODEL_CREATED"
    assert retrieved.title == "Model created"
    assert retrieved.description == "Initial model creation"
    assert retrieved.timestamp == created.timestamp
    assert retrieved.data_model_id == "model-1"
    assert retrieved.job_id == "job-1"
    assert retrieved.metadata == {
        "source": "test",
        "details": {"version": 1},
    }


def test_activities_survive_repository_restart(tmp_path: Path) -> None:
    first_repository = build_repository(tmp_path)

    created = create_activity(
        first_repository,
        "restart-test",
        metadata={"persisted": True},
    )

    restarted_repository = build_repository(tmp_path)
    activities = restarted_repository.get_recent_by_owner_user_id(
        OWNER_ID
    )

    assert len(activities) == 1
    assert activities[0].activity_id == created.activity_id
    assert activities[0].metadata == {"persisted": True}


def test_multiple_appends_preserve_all_previous_activities(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    created = [
        create_activity(repository, f"append-{index}")
        for index in range(5)
    ]

    activities = repository.get_recent_by_owner_user_id(
        OWNER_ID,
        limit=10,
    )

    assert len(activities) == 5
    assert {
        activity.activity_id for activity in activities
    } == {
        activity.activity_id for activity in created
    }


def test_workspace_activities_are_isolated_by_owner(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    create_activity(
        repository,
        "owner-a-activity",
        owner_user_id="owner-a",
    )
    create_activity(
        repository,
        "owner-b-activity",
        owner_user_id="owner-b",
    )

    owner_a = repository.get_recent_by_owner_user_id("owner-a")
    owner_b = repository.get_recent_by_owner_user_id("owner-b")

    assert len(owner_a) == 1
    assert len(owner_b) == 1
    assert owner_a[0].owner_user_id == "owner-a"
    assert owner_b[0].owner_user_id == "owner-b"
    assert owner_a[0].activity_id != owner_b[0].activity_id


def test_data_model_activities_are_isolated_by_model(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    create_activity(
        repository,
        "model-a-activity",
        data_model_id="model-a",
    )
    create_activity(
        repository,
        "model-b-activity",
        data_model_id="model-b",
    )

    model_a = repository.get_by_data_model_id("model-a")
    model_b = repository.get_by_data_model_id("model-b")

    assert len(model_a) == 1
    assert len(model_b) == 1
    assert model_a[0].data_model_id == "model-a"
    assert model_b[0].data_model_id == "model-b"
    assert model_a[0].activity_id != model_b[0].activity_id


def test_recent_activities_respect_limit_and_sort_order(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    for index in range(6):
        create_activity(repository, f"recent-{index}")

    all_activities = repository.get_recent_by_owner_user_id(
        OWNER_ID,
        limit=10,
    )
    limited_activities = repository.get_recent_by_owner_user_id(
        OWNER_ID,
        limit=3,
    )

    expected_order = sorted(
        all_activities,
        key=lambda activity: (
            activity.timestamp,
            activity.activity_id,
        ),
        reverse=True,
    )

    assert len(all_activities) == 6
    assert len(limited_activities) == 3
    assert [
        activity.activity_id for activity in limited_activities
    ] == [
        activity.activity_id for activity in expected_order[:3]
    ]
    assert repository.get_recent_by_owner_user_id(
        OWNER_ID,
        limit=0,
    ) == []


def test_concurrent_writes_across_repository_instances(
    tmp_path: Path,
) -> None:
    worker_count = 8
    activities_per_worker = 10

    def write_activities(worker_number: int) -> None:
        repository = build_repository(tmp_path)

        for index in range(activities_per_worker):
            create_activity(
                repository,
                f"thread-{worker_number}-activity-{index}",
            )

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        list(executor.map(write_activities, range(worker_count)))

    repository = build_repository(tmp_path)
    activities = repository.get_recent_by_owner_user_id(
        OWNER_ID,
        limit=worker_count * activities_per_worker + 1,
    )

    expected_count = worker_count * activities_per_worker

    assert len(activities) == expected_count
    assert len({
        activity.activity_id for activity in activities
    }) == expected_count
    assert len({
        activity.title for activity in activities
    }) == expected_count


def test_concurrent_process_writes_preserve_all_activities(
    tmp_path: Path,
) -> None:
    process_count = 4
    activities_per_process = 12

    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(
            target=_write_activities_in_process,
            args=(
                str(tmp_path),
                process_number,
                activities_per_process,
            ),
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
            raise AssertionError("Activity writer process timed out.")

        assert process.exitcode == 0

    repository = build_repository(tmp_path)
    activities = repository.get_recent_by_owner_user_id(
        OWNER_ID,
        limit=process_count * activities_per_process + 1,
    )

    expected_count = process_count * activities_per_process

    assert len(activities) == expected_count
    assert len({
        activity.activity_id for activity in activities
    }) == expected_count
    assert len({
        activity.title for activity in activities
    }) == expected_count


def activity_partition_paths(repository, activity):
    return repository._partition_paths(
        scope="workspace",
        identity=activity.owner_user_id,
        year=activity.timestamp.strftime("%Y"),
        month=activity.timestamp.strftime("%m"),
    )


def test_missing_activity_index_is_rebuilt_from_events(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    created = [
        create_activity(repository, f"missing-index-{index}")
        for index in range(2)
    ]

    event_path, index_path = activity_partition_paths(
        repository, created[0]
    )
    index_path.unlink()

    recovered = repository.get_recent_by_owner_user_id(OWNER_ID)

    assert {item.activity_id for item in recovered} == {
        item.activity_id for item in created
    }
    assert index_path.exists()

    entries = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(entries) == 2
    assert event_path.exists()


def test_corrupt_activity_index_is_rebuilt_from_events(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    created = create_activity(repository, "corrupt-index")
    _, index_path = activity_partition_paths(repository, created)

    index_path.write_text('{"invalid": }\n', encoding="utf-8")

    recovered = repository.get_recent_by_owner_user_id(OWNER_ID)

    assert len(recovered) == 1
    assert recovered[0].activity_id == created.activity_id

    entries = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(entries) == 1
    assert entries[0]["activity_id"] == created.activity_id
    assert entries[0]["offset"] == 0


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("offset", 1),
        ("length", 0),
    ],
)
def test_invalid_activity_index_offsets_are_rebuilt(
    tmp_path: Path,
    field: str,
    invalid_value: int,
) -> None:
    repository = build_repository(tmp_path)

    created = create_activity(repository, f"invalid-{field}")
    _, index_path = activity_partition_paths(repository, created)

    entries = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
    ]
    entries[0][field] = invalid_value
    index_path.write_text(
        json.dumps(entries[0]) + "\n",
        encoding="utf-8",
    )

    recovered = repository.get_recent_by_owner_user_id(OWNER_ID)

    assert len(recovered) == 1
    assert recovered[0].activity_id == created.activity_id

    rebuilt_entry = json.loads(
        index_path.read_text(encoding="utf-8").splitlines()[0]
    )
    assert rebuilt_entry["offset"] == 0
    assert rebuilt_entry["length"] > 0


@pytest.mark.parametrize(
    "malformed_position",
    ["after_valid_record", "between_valid_records"],
)
def test_malformed_complete_event_blocks_index_rebuild(
    tmp_path: Path,
    malformed_position: str,
) -> None:
    repository = build_repository(tmp_path)

    created = [
        create_activity(repository, f"malformed-source-{index}")
        for index in range(
            2 if malformed_position == "between_valid_records" else 1
        )
    ]

    event_path, index_path = activity_partition_paths(
        repository, created[0]
    )
    valid_lines = event_path.read_bytes().splitlines(keepends=True)
    malformed_line = b'{"activity_id": invalid}\n'

    if malformed_position == "between_valid_records":
        corrupted_content = (
            valid_lines[0] + malformed_line + valid_lines[1]
        )
    else:
        corrupted_content = valid_lines[0] + malformed_line

    event_path.write_bytes(corrupted_content)
    index_path.unlink()

    with pytest.raises(json.JSONDecodeError):
        repository.get_recent_by_owner_user_id(OWNER_ID)

    # Corrupt authoritative data must not be silently discarded or rewritten.
    assert event_path.read_bytes() == corrupted_content

    # A partial index must not be published as a successful reconstruction.
    assert not index_path.exists()


def test_incomplete_event_tail_is_removed_before_index_rebuild(
    tmp_path: Path,
) -> None:
    repository = build_repository(tmp_path)

    created = create_activity(repository, "incomplete-tail")
    event_path, index_path = activity_partition_paths(
        repository, created
    )

    valid_content = event_path.read_bytes()
    event_path.write_bytes(valid_content + b'{"activity_id":"unfinished"')

    index_path.unlink()

    recovered = repository.get_recent_by_owner_user_id(OWNER_ID)

    assert len(recovered) == 1
    assert recovered[0].activity_id == created.activity_id
    assert event_path.read_bytes() == valid_content
    assert index_path.exists()
