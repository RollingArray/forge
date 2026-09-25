from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceTemplate:
    name: str
    description: str
    icon: str
    accent: str
