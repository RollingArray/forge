from pydantic import BaseModel


class WorkspaceTemplateModel(BaseModel):
    name: str
    description: str
    icon: str
    accent: str
