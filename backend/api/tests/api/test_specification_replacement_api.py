import asyncio
import copy
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import specification as specification_api
from app.interfaces.auth_user import AuthUser
from app.models.specification_import_model import (
    SpecificationImportCsvModel,
    SpecificationReplacementPreviewRequest,
    SpecificationReplacementValidationRequest,
    SpecificationReplacementApplyRequest,
)
from app.repositories.json_specification_repository import (
    JsonSpecificationRepository,
)
from app.services.specification_csv_export_service import (
    SpecificationCsvExportService,
)


USER = AuthUser(
    user_id="test-user",
    email="test@example.com",
    display_name="Test User",
)
DATA_MODEL_ID = "replacement-test-model"


def rich_specification():
    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "validation_rich_specification.json"
    )
    return json.loads(fixture.read_text(encoding="utf-8"))


def exported_csv():
    return SpecificationCsvExportService().export(rich_specification())


class InMemorySpecificationRepository:
    """Isolated persistence boundary for replacement endpoint tests."""

    def __init__(self, specification):
        self.specification = copy.deepcopy(specification)
        self.save_calls = []

    @contextmanager
    def transaction(self, data_model_id):
        yield

    def read(self, data_model_id):
        return copy.deepcopy(self.specification)

    @staticmethod
    def revision(specification):
        return JsonSpecificationRepository.revision(specification)

    def save_if_revision(
        self,
        data_model_id,
        expected_revision,
        specification,
        missing_specification=None,
    ):
        current = (
            self.specification
            if self.specification is not None
            else missing_specification
        )
        current_revision = (
            self.revision(current) if current is not None else None
        )
        if current_revision != expected_revision:
            from app.repositories.json_specification_repository import (
                SpecificationRevisionConflict,
            )
            raise SpecificationRevisionConflict("Revision conflict.")

        self.specification = copy.deepcopy(specification)
        self.save_calls.append(copy.deepcopy(specification))
        return copy.deepcopy(specification)


def install_common_mocks(monkeypatch, repository, validation_result=None):
    data_model = SimpleNamespace(
        name="Test Model",
        description="Replacement API test",
        owner_user_id="owner-user",
    )

    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(can_edit=lambda **kwargs: True),
    )
    monkeypatch.setattr(
        specification_api,
        "data_model_repository",
        SimpleNamespace(
            get_by_id_any=lambda **kwargs: data_model,
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_import_repository",
        repository,
    )
    monkeypatch.setattr(
        specification_api,
        "activity_service",
        SimpleNamespace(record=lambda **kwargs: None),
    )

    if validation_result is not None:
        monkeypatch.setattr(
            specification_api,
            "specification_validation_service",
            SimpleNamespace(
                validate=lambda specification: validation_result,
            ),
        )


def preview_request(csv=None):
    return SpecificationReplacementPreviewRequest(
        csv=SpecificationImportCsvModel(**(csv or exported_csv()))
    )


def validation_request(preview, csv=None):
    csv = csv or exported_csv()
    return SpecificationReplacementValidationRequest(
        base_revision=preview["base_revision"],
        csv_digest=specification_api._replacement_csv_digest(csv),
        csv=SpecificationImportCsvModel(**csv),
    )


def apply_request(preview, csv=None):
    csv = csv or exported_csv()
    return SpecificationReplacementApplyRequest(
        base_revision=preview["base_revision"],
        csv_digest=specification_api._replacement_csv_digest(csv),
        csv=SpecificationImportCsvModel(**csv),
    )


VALIDATION_PASSED = {
    "can_continue": True,
    "errors": 0,
    "warnings": 0,
    "unsupported": 0,
    "findings": [],
}


def test_preview_returns_candidate_without_persisting(monkeypatch):
    original = rich_specification()
    repository = InMemorySpecificationRepository(original)
    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    response = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(),
            user=USER,
        )
    )

    assert response["can_apply"] is True
    assert response["candidate"]["entities"] == original["entities"]
    assert response["candidate"]["foreign_keys"] == original["foreign_keys"]
    assert response["candidate"]["relationships"] == original["relationships"]
    assert response["candidate"]["constraints"] == original["constraints"]
    assert response["base_revision"] == repository.revision(original)
    assert repository.specification == original
    assert repository.save_calls == []


def test_preview_rejects_missing_csv_section(monkeypatch):
    repository = InMemorySpecificationRepository(rich_specification())
    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    csv = exported_csv()
    csv["fields_and_keys"] = ""

    response = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )

    assert response["can_apply"] is False
    assert response["candidate"] is None
    assert response["validation"] is None
    assert any(
        issue["section"] == "fields_and_keys"
        for issue in response["issues"]
    )
    assert repository.save_calls == []


def test_preview_allows_canonical_validation_findings(monkeypatch):
    repository = InMemorySpecificationRepository(rich_specification())

    def unexpected_validation(*args, **kwargs):
        raise AssertionError(
            "Replacement preview must not invoke canonical validation."
        )

    install_common_mocks(monkeypatch, repository)
    monkeypatch.setattr(
        specification_api,
        "specification_validation_service",
        SimpleNamespace(validate=unexpected_validation),
    )

    response = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(),
            user=USER,
        )
    )

    assert response["can_apply"] is True
    assert response["validation"] is None
    assert response["candidate"] is not None
    assert repository.save_calls == []


def test_validate_replacement_returns_canonical_validation_without_persisting(
    monkeypatch,
):
    original = rich_specification()
    repository = InMemorySpecificationRepository(original)
    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )

    response = asyncio.run(
        specification_api.specification_replacement_validate(
            data_model_id=DATA_MODEL_ID,
            request=validation_request(preview, csv),
            user=USER,
        )
    )

    assert response["base_revision"] == preview["base_revision"]
    assert response["csv_digest"] == preview["csv_digest"]
    assert response["validation"] == VALIDATION_PASSED
    assert response["specification"] == preview["candidate"]
    assert repository.save_calls == []
    assert repository.specification == original


def test_validate_replacement_returns_invalid_findings_without_persisting(
    monkeypatch,
):
    original = rich_specification()
    repository = InMemorySpecificationRepository(original)

    invalid_result = {
        "can_continue": False,
        "errors": 1,
        "warnings": 0,
        "passed": 0,
        "total_checks": 1,
        "findings": [
            {
                "id": "validation-1",
                "severity": "error",
                "category": "Specification",
                "title": "Invalid candidate",
                "details": "Candidate failed canonical validation.",
                "entity": None,
                "field": None,
                "remediation": None,
            }
        ],
    }

    install_common_mocks(monkeypatch, repository, invalid_result)

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )

    response = asyncio.run(
        specification_api.specification_replacement_validate(
            data_model_id=DATA_MODEL_ID,
            request=validation_request(preview, csv),
            user=USER,
        )
    )

    assert response["validation"] == invalid_result
    assert response["validation"]["can_continue"] is False
    assert repository.save_calls == []
    assert repository.specification == original


def test_validate_replacement_rejects_stale_revision(monkeypatch):
    repository = InMemorySpecificationRepository(rich_specification())
    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )
    request = validation_request(preview, csv)

    repository.specification["model"]["description"] = "Changed after preparation"

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            specification_api.specification_replacement_validate(
                data_model_id=DATA_MODEL_ID,
                request=request,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 409
    assert repository.save_calls == []


def test_validate_replacement_rejects_csv_digest_mismatch(monkeypatch):
    repository = InMemorySpecificationRepository(rich_specification())
    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )
    request = validation_request(preview, csv)
    request.csv_digest = "0" * 64

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            specification_api.specification_replacement_validate(
                data_model_id=DATA_MODEL_ID,
                request=request,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 409
    assert repository.save_calls == []


def test_apply_persists_validated_replacement(monkeypatch):
    original = rich_specification()
    repository = InMemorySpecificationRepository(original)
    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )
    request = apply_request(preview, csv)

    response = asyncio.run(
        specification_api.specification_replacement_apply(
            data_model_id=DATA_MODEL_ID,
            request=request,
            user=USER,
        )
    )

    assert response["applied"] is True
    assert response["specification_revision"] == repository.revision(
        repository.specification
    )
    assert len(repository.save_calls) == 1
    assert repository.specification["entities"] == original["entities"]
    assert repository.specification["foreign_keys"] == original["foreign_keys"]
    assert repository.specification["relationships"] == original["relationships"]
    assert repository.specification["constraints"] == original["constraints"]


def test_apply_rejects_csv_digest_mismatch(monkeypatch):
    repository = InMemorySpecificationRepository(rich_specification())
    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )
    request = apply_request(preview, csv).model_copy(
        update={"csv_digest": "0" * 64}
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            specification_api.specification_replacement_apply(
                data_model_id=DATA_MODEL_ID,
                request=request,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 409
    assert repository.save_calls == []


def test_apply_rejects_stale_revision(monkeypatch):
    repository = InMemorySpecificationRepository(rich_specification())
    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )
    request = apply_request(preview, csv)

    # Simulate another writer changing the canonical specification
    # after preview but before apply.
    repository.specification["model"]["description"] = "Changed after preview"

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            specification_api.specification_replacement_apply(
                data_model_id=DATA_MODEL_ID,
                request=request,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 409
    assert repository.save_calls == []


def test_apply_rejects_canonically_invalid_replacement(monkeypatch):
    original = rich_specification()
    repository = InMemorySpecificationRepository(original)
    original_snapshot = json.loads(json.dumps(original))
    validation_calls = []

    def reject_candidate(candidate):
        validation_calls.append(candidate)
        return {
            "can_continue": False,
            "errors": 1,
            "warnings": 0,
            "passed": 0,
            "total_checks": 1,
            "findings": [
                {
                    "id": "validation-1",
                    "severity": "error",
                    "category": "Specification",
                    "title": "Invalid candidate",
                    "details": "Candidate failed canonical validation.",
                    "entity": None,
                    "field": None,
                    "remediation": None,
                }
            ],
        }

    install_common_mocks(monkeypatch, repository)
    monkeypatch.setattr(
        specification_api,
        "specification_validation_service",
        SimpleNamespace(validate=reject_candidate),
    )

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )
    request = apply_request(preview, csv)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            specification_api.specification_replacement_apply(
                data_model_id=DATA_MODEL_ID,
                request=request,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 422
    assert validation_calls
    assert len(validation_calls) == 1
    assert repository.save_calls == []
    assert repository.specification == original_snapshot


def test_apply_with_real_repository_supports_nested_transactions_and_reload(
    tmp_path,
    monkeypatch,
):
    original = rich_specification()

    repository = JsonSpecificationRepository()
    repository._data_directory = tmp_path
    repository.save(DATA_MODEL_ID, original)

    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )
    assert preview["can_apply"] is True

    response = asyncio.run(
        specification_api.specification_replacement_apply(
            data_model_id=DATA_MODEL_ID,
            request=apply_request(preview, csv),
            user=USER,
        )
    )

    assert response["applied"] is True

    # A new repository instance must observe the committed file contents.
    reopened_repository = JsonSpecificationRepository()
    reopened_repository._data_directory = tmp_path
    persisted = reopened_repository.read(DATA_MODEL_ID)

    assert persisted == preview["candidate"]
    assert (
        reopened_repository.revision(persisted)
        == response["specification_revision"]
    )

    specification_path = (
        tmp_path
        / "data_model"
        / DATA_MODEL_ID
        / "specification.json"
    )
    assert specification_path.is_file()
    assert not specification_path.with_suffix(".tmp").exists()


def test_real_repository_rejects_stale_revision_without_overwriting(
    tmp_path,
    monkeypatch,
):
    original = rich_specification()

    repository = JsonSpecificationRepository()
    repository._data_directory = tmp_path
    repository.save(DATA_MODEL_ID, original)

    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )
    request = apply_request(preview, csv)

    # Simulate an independent writer changing the canonical file after preview.
    concurrent_repository = JsonSpecificationRepository()
    concurrent_repository._data_directory = tmp_path
    changed = concurrent_repository.read(DATA_MODEL_ID)
    changed["model"]["description"] = "Changed by another writer"
    concurrent_repository.save(DATA_MODEL_ID, changed)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            specification_api.specification_replacement_apply(
                data_model_id=DATA_MODEL_ID,
                request=request,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 409

    reopened_repository = JsonSpecificationRepository()
    reopened_repository._data_directory = tmp_path
    persisted = reopened_repository.read(DATA_MODEL_ID)

    assert persisted["model"]["description"] == "Changed by another writer"
    assert (
        reopened_repository.revision(persisted)
        == concurrent_repository.revision(changed)
    )
    assert not (
        tmp_path
        / "data_model"
        / DATA_MODEL_ID
        / "specification.tmp"
    ).exists()


def test_activity_failure_does_not_report_committed_replacement_as_failed(
    monkeypatch,
):
    original = rich_specification()
    repository = InMemorySpecificationRepository(original)

    install_common_mocks(monkeypatch, repository, VALIDATION_PASSED)
    monkeypatch.setattr(
        specification_api,
        "activity_service",
        SimpleNamespace(
            record=lambda **kwargs: (_ for _ in ()).throw(
                OSError("Activity store unavailable")
            )
        ),
    )

    csv = exported_csv()
    preview = asyncio.run(
        specification_api.specification_replacement_preview(
            data_model_id=DATA_MODEL_ID,
            request=preview_request(csv),
            user=USER,
        )
    )

    response = asyncio.run(
        specification_api.specification_replacement_apply(
            data_model_id=DATA_MODEL_ID,
            request=apply_request(preview, csv),
            user=USER,
        )
    )

    assert response["applied"] is True
    assert len(repository.save_calls) == 1
    assert repository.specification == preview["candidate"]



def test_export_returns_all_five_csv_sections_without_mutation(monkeypatch):
    original = rich_specification()
    repository = InMemorySpecificationRepository(original)

    install_common_mocks(monkeypatch, repository)

    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(
            can_view=lambda **kwargs: True,
            can_edit=lambda **kwargs: False,
        ),
    )
    monkeypatch.setattr(
        specification_api,
        "specification_service",
        SimpleNamespace(
            get_specification=lambda **kwargs: copy.deepcopy(original),
        ),
    )

    response = asyncio.run(
        specification_api.specification_replacement_export(
            data_model_id=DATA_MODEL_ID,
            user=USER,
        )
    )

    exporter = SpecificationCsvExportService()

    assert set(response) == {
        "entities",
        "fields_and_keys",
        "foreign_keys",
        "relationships",
        "constraints",
    }

    for section, headers in exporter.SECTION_HEADERS.items():
        assert response[section].splitlines()[0] == ",".join(headers)

    assert repository.specification == original
    assert repository.save_calls == []


def test_export_rejects_user_without_view_access(monkeypatch):
    monkeypatch.setattr(
        specification_api,
        "data_model_access_service",
        SimpleNamespace(can_view=lambda **kwargs: False),
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            specification_api.specification_replacement_export(
                data_model_id=DATA_MODEL_ID,
                user=USER,
            )
        )

    assert exc_info.value.status_code == 404
