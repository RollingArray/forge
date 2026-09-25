from app.interfaces.data_model_repository import DataModelRepository
from app.interfaces.workspace_metrics import WorkspaceMetrics
from app.interfaces.workspace_template import WorkspaceTemplate
from app.interfaces.workspace_activity import WorkspaceActivity
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)


class WorkspaceService:
    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
    ) -> None:
        self._data_model_repository = (
            data_model_repository
            if data_model_repository is not None
            else JsonDataModelRepository()
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
        return []
