"""
File: workspace_service.py
Purpose: FORGE workspace business service.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from app.constants.activity import (
    ACTIVITY_PRESENTATION,
    ActivityType,
)
from app.interfaces.activity import Activity
from app.interfaces.data_model_repository import DataModelRepository
from app.interfaces.workspace_activity import WorkspaceActivity
from app.interfaces.workspace_metrics import WorkspaceMetrics
from app.interfaces.workspace_template import WorkspaceTemplate
from app.repositories.json_activity_repository import (
    JsonActivityRepository,
)
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)
from app.services.activity_service import ActivityService


class WorkspaceService:
    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
        activity_service: ActivityService | None = None,
    ) -> None:
        self._data_model_repository = (
            data_model_repository
            if data_model_repository is not None
            else JsonDataModelRepository()
        )
        self._activity_service = (
            activity_service
            if activity_service is not None
            else ActivityService(
                activity_repository=JsonActivityRepository(),
            )
        )

    def get_metrics(
        self,
        owner_user_id: str,
    ) -> WorkspaceMetrics:
        data_models = self._data_model_repository.get_by_owner_user_id(
            owner_user_id=owner_user_id,
        )

        return WorkspaceMetrics(
            total_data_models=len(data_models),
            total_entities=0,
            generated_datasets=0,
            total_records=0,
        )

    def get_templates(self) -> list[WorkspaceTemplate]:
        return [
            WorkspaceTemplate(
                name="SAP Template",
                description="Common SAP tables with standard relationships",
                icon="table_view",
                accent="blue",
            ),
            WorkspaceTemplate(
                name="Manufacturing Template",
                description="MES and production data model",
                icon="factory",
                accent="green",
            ),
            WorkspaceTemplate(
                name="CRM Template",
                description="Customer and sales data model",
                icon="groups",
                accent="purple",
            ),
            WorkspaceTemplate(
                name="Blank Template",
                description="Start with an empty model",
                icon="description",
                accent="gray",
            ),
        ]

    def get_activity(
        self,
        owner_user_id: str,
    ) -> list[WorkspaceActivity]:
        activities = self._activity_service.get_recent(
            owner_user_id=owner_user_id,
            limit=10,
        )

        return [
            self._to_workspace_activity(
                activity=activity,
                owner_user_id=owner_user_id,
            )
            for activity in activities
        ]

    def _to_workspace_activity(
        self,
        activity: Activity,
        owner_user_id: str,
    ) -> WorkspaceActivity:
        try:
            activity_type = ActivityType(activity.type)
        except ValueError:
            activity_type = ActivityType.USER_SIGNED_IN

        presentation = ACTIVITY_PRESENTATION[activity_type]

        data_model = "FORGE"

        if activity.data_model_id:
            data_model_entity = self._data_model_repository.get_by_id(
                data_model_id=activity.data_model_id,
                owner_user_id=owner_user_id,
            )

            if data_model_entity is not None:
                data_model = data_model_entity.name
            elif activity.metadata:
                historical_name = activity.metadata.get("data_model_name")

                if isinstance(historical_name, str) and historical_name.strip():
                    data_model = historical_name

        return WorkspaceActivity(
            action=activity.title,
            data_model=data_model,
            time=activity.timestamp.isoformat(),
            icon=presentation.icon,
            accent=presentation.accent,
        )
