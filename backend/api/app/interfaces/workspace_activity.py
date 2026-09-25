from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceActivity:
    """Define the presentation contract for Workspace activity."""

    action: str
    description: str
    data_model: str
    actor: str
    target: str | None
    time: str
    icon: str
    accent: str
