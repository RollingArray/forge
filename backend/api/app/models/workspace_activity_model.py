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
