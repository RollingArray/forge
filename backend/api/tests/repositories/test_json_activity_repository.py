import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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
