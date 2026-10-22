from pydantic import BaseModel


class WorkspaceActivityModel(BaseModel):
    """API representation of Workspace activity."""

    action: str
    description: str
    data_model: str
    actor: str
    target: str | None
    time: str
    icon: str
    accent: str


class WorkspaceActivityPageModel(BaseModel):
    """Paginated API representation of Workspace activity."""

    activities: list[WorkspaceActivityModel]
    offset: int
    limit: int
    has_more: bool
