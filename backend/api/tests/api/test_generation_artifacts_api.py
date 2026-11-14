import asyncio
import csv
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import generation as generation_api
from app.interfaces.auth_user import AuthUser


USER = AuthUser(
    user_id="test-user",
    email="test@example.com",
    display_name="Test User",
)

DATA_MODEL_ID = "test-model"
JOB_ID = "test-job"
ENTITY_NAME = "Customer"


def make_job(**overrides):
    values = {
        "data_model_id": DATA_MODEL_ID,
        "job_id": JOB_ID,
        "entities": [
            SimpleNamespace(
                entity_name=ENTITY_NAME,
                generated_rows=3,
            ),
        ],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def configure_access(monkeypatch, allowed=True):
    monkeypatch.setattr(
        generation_api,
        "data_model_access_service",
        SimpleNamespace(can_generate=lambda **kwargs: allowed),
    )


def configure_job(monkeypatch, job):
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(get_job=lambda **kwargs: job),
    )


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["id", "name"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def configure_artifact(monkeypatch, path):
    monkeypatch.setattr(
        generation_api,
        "artifact_writer",
        SimpleNamespace(
            get_entity_csv_path=lambda **kwargs: path,
        ),
    )


def sample_rows():
    return [
        {"id": "1", "name": "Alpha"},
        {"id": "2", "name": "Beta"},
        {"id": "3", "name": "Gamma"},
    ]


def test_list_generation_artifacts_returns_existing_csv_files(
    monkeypatch,
    tmp_path,
):
    artifact = write_csv(
        tmp_path / "Customer.csv",
        sample_rows(),
    )
    missing = tmp_path / "Order.csv"

    job = make_job(
        entities=[
            SimpleNamespace(entity_name="Customer"),
            SimpleNamespace(entity_name="Order"),
        ],
    )

    configure_access(monkeypatch)
    configure_job(monkeypatch, job)

    monkeypatch.setattr(
        generation_api,
        "artifact_writer",
        SimpleNamespace(
            get_entity_csv_path=lambda data_model_id, job_id, entity_name:
                artifact if entity_name == "Customer" else missing,
        ),
    )

    response = asyncio.run(
        generation_api.list_generation_artifacts(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            user=USER,
        )
    )

    assert len(response) == 1
    assert response[0].entity_name == "Customer"
    assert response[0].filename == "Customer.csv"
    assert response[0].rows == 3
    assert response[0].size_bytes == artifact.stat().st_size


def test_preview_generation_artifact_returns_at_most_ten_rows(
    monkeypatch,
    tmp_path,
):
    rows = [
        {"id": str(index), "name": f"Customer {index}"}
        for index in range(15)
    ]
    artifact = write_csv(tmp_path / "Customer.csv", rows)

    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job())
    configure_artifact(monkeypatch, artifact)

    response = asyncio.run(
        generation_api.preview_generation_artifact(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name=ENTITY_NAME,
            user=USER,
        )
    )

    assert response.entity_name == ENTITY_NAME
    assert response.filename == "Customer.csv"
    assert response.columns == ["id", "name"]
    assert response.total_rows == 15
    assert response.preview_rows == 10
    assert len(response.rows) == 10


def test_get_generation_artifact_data_supports_pagination(
    monkeypatch,
    tmp_path,
):
    artifact = write_csv(tmp_path / "Customer.csv", sample_rows())

    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job())
    configure_artifact(monkeypatch, artifact)

    response = asyncio.run(
        generation_api.get_generation_artifact_data(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name=ENTITY_NAME,
            offset=1,
            limit=1,
            user=USER,
        )
    )

    assert response.entity_name == ENTITY_NAME
    assert response.columns == ["id", "name"]
    assert response.rows == [{"id": "2", "name": "Beta"}]
    assert response.total_rows == 3
    assert response.offset == 1
    assert response.limit == 1


def test_get_generation_artifact_data_supports_case_insensitive_search(
    monkeypatch,
    tmp_path,
):
    artifact = write_csv(tmp_path / "Customer.csv", sample_rows())

    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job())
    configure_artifact(monkeypatch, artifact)

    response = asyncio.run(
        generation_api.get_generation_artifact_data(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name=ENTITY_NAME,
            search="BETA",
            user=USER,
        )
    )

    assert response.rows == [{"id": "2", "name": "Beta"}]
    assert response.total_rows == 1
    assert response.search == "beta"


def test_download_generation_artifact_returns_csv_and_records_activity(
    monkeypatch,
    tmp_path,
):
    artifact = write_csv(tmp_path / "Customer.csv", sample_rows())

    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job())
    configure_artifact(monkeypatch, artifact)

    recorded = []
    monkeypatch.setattr(
        generation_api,
        "data_model_repository",
        SimpleNamespace(
            get_by_id_any=lambda data_model_id: SimpleNamespace(
                owner_user_id="owner-user",
                name="Test Model",
            ),
        ),
    )
    monkeypatch.setattr(
        generation_api,
        "activity_service",
        SimpleNamespace(record=lambda **kwargs: recorded.append(kwargs)),
    )

    response = asyncio.run(
        generation_api.download_generation_artifact(
            data_model_id=DATA_MODEL_ID,
            job_id=JOB_ID,
            entity_name=ENTITY_NAME,
            user=USER,
        )
    )

    assert Path(response.path) == artifact
    assert response.filename == "Customer.csv"
    assert response.media_type == "text/csv"

    assert len(recorded) == 1
    assert recorded[0]["owner_user_id"] == "owner-user"
    assert recorded[0]["actor_user_id"] == USER.user_id
    assert recorded[0]["data_model_id"] == DATA_MODEL_ID
    assert recorded[0]["job_id"] == JOB_ID
    assert recorded[0]["metadata"]["entity_name"] == ENTITY_NAME
    assert recorded[0]["metadata"]["format"] == "csv"


@pytest.mark.parametrize(
    "route,kwargs",
    [
        (
            generation_api.list_generation_artifacts,
            {},
        ),
        (
            generation_api.preview_generation_artifact,
            {"entity_name": ENTITY_NAME},
        ),
        (
            generation_api.get_generation_artifact_data,
            {"entity_name": ENTITY_NAME},
        ),
        (
            generation_api.download_generation_artifact,
            {"entity_name": ENTITY_NAME},
        ),
    ],
)
def test_artifact_routes_return_404_when_access_is_denied(
    monkeypatch,
    route,
    kwargs,
):
    configure_access(monkeypatch, allowed=False)
    monkeypatch.setattr(
        generation_api,
        "generation_service",
        SimpleNamespace(
            get_job=lambda **kwargs: pytest.fail(
                "Job lookup must not occur when access is denied."
            )
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            route(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
                **kwargs,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Data model not found."


@pytest.mark.parametrize(
    "route,kwargs",
    [
        (
            generation_api.list_generation_artifacts,
            {},
        ),
        (
            generation_api.preview_generation_artifact,
            {"entity_name": ENTITY_NAME},
        ),
        (
            generation_api.get_generation_artifact_data,
            {"entity_name": ENTITY_NAME},
        ),
        (
            generation_api.download_generation_artifact,
            {"entity_name": ENTITY_NAME},
        ),
    ],
)
@pytest.mark.parametrize(
    "job",
    [
        None,
        make_job(data_model_id="another-model"),
    ],
    ids=["missing-job", "mismatched-model"],
)
def test_artifact_routes_return_404_for_missing_or_mismatched_jobs(
    monkeypatch,
    route,
    kwargs,
    job,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, job)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            route(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
                **kwargs,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generation job not found."


@pytest.mark.parametrize(
    "route,kwargs",
    [
        (
            generation_api.preview_generation_artifact,
            {"entity_name": "Unrelated"},
        ),
        (
            generation_api.get_generation_artifact_data,
            {"entity_name": "Unrelated"},
        ),
        (
            generation_api.download_generation_artifact,
            {"entity_name": "Unrelated"},
        ),
    ],
)
def test_entity_routes_reject_entities_not_in_generation_job(
    monkeypatch,
    tmp_path,
    route,
    kwargs,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job())
    configure_artifact(monkeypatch, tmp_path / "Unrelated.csv")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            route(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                user=USER,
                **kwargs,
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Generated artifact not found."


def test_preview_rejects_invalid_entity_path(
    monkeypatch,
):
    configure_access(monkeypatch)
    configure_job(monkeypatch, make_job())

    monkeypatch.setattr(
        generation_api,
        "artifact_writer",
        SimpleNamespace(
            get_entity_csv_path=lambda **kwargs: (_ for _ in ()).throw(
                ValueError("Invalid entity name.")
            ),
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.preview_generation_artifact(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                entity_name="../Customer",
                user=USER,
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid entity name."


@pytest.mark.parametrize(
    "offset,limit",
    [
        (-1, 10),
        (0, 0),
        (0, 201),
    ],
)
def test_get_generation_artifact_data_rejects_invalid_pagination(
    offset,
    limit,
):
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            generation_api.get_generation_artifact_data(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                entity_name=ENTITY_NAME,
                offset=offset,
                limit=limit,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 400
