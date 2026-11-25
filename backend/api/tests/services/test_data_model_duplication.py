
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.constants.activity import ActivityType
from app.interfaces.data_model import DataModel
from app.services.data_model_service import DataModelService


OWNER_ID = "owner-1"
SOURCE_ID = "source-model-123456"
SOURCE_NAME = "Aerospace Supply Chain"


def make_model(model_id, name, owner=OWNER_ID):
    now = datetime.now(timezone.utc)
    return DataModel(
        data_model_id=model_id,
        owner_user_id=owner,
        name=name,
        description="Supply chain model",
        color="#7C5CFC",
        tags=["Aerospace", "Supply Chain"],
        status="Draft",
        created_at=now,
        updated_at=now,
    )


def make_service(specification=None, save_error=None, activity_error=None):
    source = make_model(SOURCE_ID, SOURCE_NAME)
    duplicate = make_model("new-model-987654", "placeholder")

    models = Mock()
    models.get_by_id.return_value = source
    models.create.return_value = duplicate

    specs = Mock()
    specs.read.return_value = deepcopy(specification)
    specs.save.side_effect = save_error

    activity = Mock()
    activity.record.side_effect = activity_error

    access = Mock()

    service = DataModelService(
        data_model_repository=models,
        activity_service=activity,
        data_model_access_service=access,
        specification_repository=specs,
    )

    return service, models, specs, activity, duplicate


def valid_specification():
    return {
        "version": "1.0.0",
        "model": {
            "name": SOURCE_NAME,
            "description": "Original specification description",
        },
        "entities": [{"name": "SUPPLIER"}],
        "unknown_future_property": {
            "preserve": True,
            "nested": [1, 2, 3],
        },
    }


def test_duplicate_preserves_specification_and_creates_new_identity():
    original = valid_specification()
    service, models, specs, activity, duplicate = make_service(
        specification=original
    )

    result = service.duplicate_data_model(SOURCE_ID, OWNER_ID)

    expected_name = f"Copy of {SOURCE_NAME} - {SOURCE_ID}"

    assert result == duplicate
    assert result.data_model_id != SOURCE_ID

    models.create.assert_called_once_with(
        owner_user_id=OWNER_ID,
        name=expected_name,
        description="Supply chain model",
        color="#7C5CFC",
        tags=["Aerospace", "Supply Chain"],
    )

    copied = specs.save.call_args.args[1]
    expected = deepcopy(original)
    expected["model"]["name"] = expected_name

    assert copied == expected
    assert original["model"]["name"] == SOURCE_NAME
    assert copied["unknown_future_property"] == {
        "preserve": True,
        "nested": [1, 2, 3],
    }

    activity.record.assert_called_once()
    event = activity.record.call_args.kwargs
    assert event["activity_type"] == ActivityType.DATA_MODEL_DUPLICATED
    assert event["data_model_id"] == duplicate.data_model_id
    assert event["metadata"]["source_data_model_id"] == SOURCE_ID


def test_non_owner_cannot_duplicate_model():
    service, models, specs, activity, _ = make_service(
        specification=valid_specification()
    )
    models.get_by_id.return_value = None

    result = service.duplicate_data_model(SOURCE_ID, "another-user")

    assert result is None
    models.create.assert_not_called()
    specs.read.assert_not_called()


def test_missing_specification_does_not_create_model():
    service, models, specs, activity, _ = make_service(
        specification=None
    )

    result = service.duplicate_data_model(SOURCE_ID, OWNER_ID)

    assert result is None
    models.create.assert_not_called()


def test_invalid_model_object_is_rejected():
    service, models, specs, activity, _ = make_service(
        specification={"model": "invalid"}
    )

    with pytest.raises(ValueError, match="valid model object"):
        service.duplicate_data_model(SOURCE_ID, OWNER_ID)

    models.create.assert_not_called()


def test_specification_save_failure_rolls_back_metadata():
    service, models, specs, activity, duplicate = make_service(
        specification=valid_specification(),
        save_error=OSError("simulated write failure"),
    )

    with pytest.raises(OSError, match="simulated write failure"):
        service.duplicate_data_model(SOURCE_ID, OWNER_ID)

    specs.delete.assert_called_once_with(duplicate.data_model_id)
    models.delete.assert_called_once_with(
        data_model_id=duplicate.data_model_id,
        owner_user_id=OWNER_ID,
    )


def test_activity_failure_does_not_fail_duplication():
    service, models, specs, activity, duplicate = make_service(
        specification=valid_specification(),
        activity_error=OSError("simulated activity failure"),
    )

    result = service.duplicate_data_model(SOURCE_ID, OWNER_ID)

    assert result == duplicate
    specs.save.assert_called_once()
    models.delete.assert_not_called()
