import pytest

from app.services.generation_job_control_store import (
    GenerationJobControlRequest,
    GenerationJobControlStore,
)


@pytest.fixture
def store(tmp_path):
    instance = GenerationJobControlStore()
    instance._root = tmp_path
    return instance


def test_control_request_round_trip(store):
    result = store.request(
        "model-1",
        "job-1",
        GenerationJobControlRequest.PAUSE,
    )

    assert result == GenerationJobControlRequest.PAUSE
    assert store.get_request("model-1", "job-1") == result


def test_cancel_takes_precedence_over_pause(store):
    store.request(
        "model-1",
        "job-1",
        GenerationJobControlRequest.CANCEL,
    )

    result = store.request(
        "model-1",
        "job-1",
        GenerationJobControlRequest.PAUSE,
    )

    assert result == GenerationJobControlRequest.CANCEL
    assert store.get_request("model-1", "job-1") == result


def test_pause_can_be_upgraded_to_cancel(store):
    store.request(
        "model-1",
        "job-1",
        GenerationJobControlRequest.PAUSE,
    )

    result = store.request(
        "model-1",
        "job-1",
        GenerationJobControlRequest.CANCEL,
    )

    assert result == GenerationJobControlRequest.CANCEL


def test_clear_request_is_durable_and_idempotent(store):
    store.request(
        "model-1",
        "job-1",
        GenerationJobControlRequest.PAUSE,
    )

    store.clear_request("model-1", "job-1")
    store.clear_request("model-1", "job-1")

    assert store.get_request("model-1", "job-1") is None


def test_missing_request_returns_none(store):
    assert store.get_request("model-1", "missing-job") is None


def test_invalid_request_value_is_rejected(store):
    path = store._control_path("model-1", "job-1")
    path.parent.mkdir(parents=True)
    path.write_text("INVALID", encoding="utf-8")

    with pytest.raises(Exception, match="Invalid generation control request"):
        store.get_request("model-1", "job-1")


@pytest.mark.parametrize(
    ("control_request", "expected_status"),
    [
        (
            GenerationJobControlRequest.PAUSE,
            "PAUSED",
        ),
        (
            GenerationJobControlRequest.CANCEL,
            "CANCELLED",
        ),
    ],
)
def test_control_request_maps_to_job_status(
    control_request,
    expected_status,
):
    from app.models.generation_model import GenerationJobStatus

    status = {
        GenerationJobControlRequest.PAUSE:
            GenerationJobStatus.PAUSED,
        GenerationJobControlRequest.CANCEL:
            GenerationJobStatus.CANCELLED,
    }[control_request]

    assert status.value == expected_status


def test_conditional_clear_removes_matching_request(store):
    store.request(
        "model-1",
        "job-1",
        GenerationJobControlRequest.PAUSE,
    )

    cleared = store.clear_request_if_matches(
        "model-1",
        "job-1",
        GenerationJobControlRequest.PAUSE,
    )

    assert cleared is True
    assert store.get_request("model-1", "job-1") is None


def test_conditional_clear_preserves_upgraded_cancel(store):
    store.request(
        "model-1",
        "job-1",
        GenerationJobControlRequest.PAUSE,
    )

    store.request(
        "model-1",
        "job-1",
        GenerationJobControlRequest.CANCEL,
    )

    cleared = store.clear_request_if_matches(
        "model-1",
        "job-1",
        GenerationJobControlRequest.PAUSE,
    )

    assert cleared is False
    assert store.get_request(
        "model-1",
        "job-1",
    ) == GenerationJobControlRequest.CANCEL


def test_conditional_clear_is_idempotent(store):
    assert store.clear_request_if_matches(
        "model-1",
        "missing-job",
        GenerationJobControlRequest.PAUSE,
    ) is False


def test_conditional_clear_rejects_invalid_expected_request(store):
    with pytest.raises(TypeError):
        store.clear_request_if_matches(
            "model-1",
            "job-1",
            "PAUSE",
        )
