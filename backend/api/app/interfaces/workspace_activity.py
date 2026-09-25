from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceActivity:
    action: str
    data_model: str
    time: str
    icon: str
    accent: str
