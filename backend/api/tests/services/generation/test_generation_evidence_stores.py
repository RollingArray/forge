import json
from pathlib import Path

import pytest

from app.services import generation_file_persistence as persistence
from app.services.generation_quality_store import GenerationQualityStore
from app.services.generation_validation_store import GenerationValidationStore


@pytest.fixture(
    params=[
        (GenerationValidationStore, "validation", "_validation_path"),
        (GenerationQualityStore, "quality", "_quality_path"),
    ],
    ids=["validation", "quality"],
)
def evidence_store(request, tmp_path: Path, monkeypatch):
    store_class, payload_key, path_method = request.param

    store = store_class()
    monkeypatch.setattr(store, "_root", tmp_path)

    return store, payload_key, getattr(store, path_method)


def test_evidence_store_round_trip(
    evidence_store,
) -> None:
    store, payload_key, _ = evidence_store

    payload = {
        "status": "passed",
        "summary": {
            "records_checked": 1200,
            "issues": 0,
        },
    }

    store.save(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        **{payload_key: payload},
    )

    result = store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
    )

    assert result == payload


def test_evidence_store_returns_none_when_file_is_missing(
    evidence_store,
) -> None:
    store, _, _ = evidence_store

    result = store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
    )

    assert result is None


@pytest.mark.parametrize(
    "content",
    [
        "{invalid json",
        "[]",
        '{"validation": null, "quality": null}',
    ],
)
def test_evidence_store_returns_none_for_invalid_document(
    evidence_store,
    content: str,
) -> None:
    store, payload_key, path_method = evidence_store

    path = path_method(
        "FORGE-DATA-MODEL-TEST",
        "FORGE-TEST",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    result = store.get(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
    )

    assert result is None


def test_evidence_store_preserves_existing_file_when_replace_fails(
    evidence_store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, payload_key, path_method = evidence_store

    original = {"status": "original"}
    replacement = {"status": "replacement"}

    store.save(
        data_model_id="FORGE-DATA-MODEL-TEST",
        job_id="FORGE-TEST",
        **{payload_key: original},
    )

    path = path_method(
        "FORGE-DATA-MODEL-TEST",
        "FORGE-TEST",
    )
    original_document = json.loads(path.read_text(encoding="utf-8"))

    def fail_replace(source: Path, destination: Path) -> None:
        raise PermissionError("access denied")

    monkeypatch.setattr(
        persistence.os,
        "replace",
        fail_replace,
    )

    with pytest.raises(PermissionError, match="access denied"):
        store.save(
            data_model_id="FORGE-DATA-MODEL-TEST",
            job_id="FORGE-TEST",
            **{payload_key: replacement},
        )

    assert json.loads(path.read_text(encoding="utf-8")) == original_document

    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []
