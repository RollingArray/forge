from fastapi import APIRouter, Depends, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.models.workspace_metrics_model import WorkspaceMetricsModel
from app.models.workspace_template_model import WorkspaceTemplateModel
from app.models.workspace_activity_model import WorkspaceActivityModel
from app.services.workspace_service import WorkspaceService


router = APIRouter(
    prefix="/workspace",
    tags=["Workspace"],
)

workspace_service = WorkspaceService()


@router.get(
    "/metrics",
    response_model=WorkspaceMetricsModel,
    status_code=status.HTTP_200_OK,
)
async def get_workspace_metrics(
    user: AuthUser = Depends(get_authenticated_user),
) -> WorkspaceMetricsModel:
    metrics = workspace_service.get_metrics(
        owner_user_id=user.user_id,
    )

    return WorkspaceMetricsModel(
        total_data_models=metrics.total_data_models,
        total_entities=metrics.total_entities,
        generated_datasets=metrics.generated_datasets,
        total_records=metrics.total_records,
    )


@router.get(
    "/templates",
    response_model=list[WorkspaceTemplateModel],
    status_code=status.HTTP_200_OK,
)
async def get_workspace_templates() -> list[WorkspaceTemplateModel]:
    templates = workspace_service.get_templates()

    return [
        WorkspaceTemplateModel(
            name=template.name,
            description=template.description,
            icon=template.icon,
            accent=template.accent,
        )
        for template in templates
    ]


@router.get(
    "/activity",
    response_model=list[WorkspaceActivityModel],
    status_code=status.HTTP_200_OK,
)
async def get_workspace_activity(
    user: AuthUser = Depends(get_authenticated_user),
) -> list[WorkspaceActivityModel]:
    activities = workspace_service.get_activity(
        owner_user_id=user.user_id,
    )

    return [
        WorkspaceActivityModel(
            action=activity.action,
            data_model=activity.data_model,
            time=activity.time,
            icon=activity.icon,
            accent=activity.accent,
        )
        for activity in activities
    ]
