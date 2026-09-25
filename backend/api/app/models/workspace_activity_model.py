from pydantic import BaseModel


class WorkspaceActivityModel(BaseModel):
    action: str
    data_model: str
    time: str
    icon: str
    accent: str
