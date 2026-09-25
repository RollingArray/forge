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
from app.interfaces.user_repository import UserRepository
from app.interfaces.workspace_activity import WorkspaceActivity
from app.interfaces.workspace_metrics import WorkspaceMetrics
from app.interfaces.workspace_template import WorkspaceTemplate
from app.repositories.json_activity_repository import (
    JsonActivityRepository,
)
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)
from app.repositories.json_data_model_access_repository import (
    JsonDataModelAccessRepository,
)
from app.services.json_user_repository import JsonUserRepository
from app.services.activity_service import ActivityService


class WorkspaceService:
    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
        activity_service: ActivityService | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        self._data_model_repository = (
            data_model_repository
            if data_model_repository is not None
            else JsonDataModelRepository()
        )
        self._data_model_access_repository = (
            JsonDataModelAccessRepository()
        )
        self._activity_service = (
            activity_service
            if activity_service is not None
            else ActivityService(
                activity_repository=JsonActivityRepository(),
            )
        )
        self._user_repository = (
            user_repository
            if user_repository is not None
            else JsonUserRepository()
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
        """Return recent activity across all Data Models visible to the user."""

        # Workspace-level activity such as sign-in is scoped to the
        # authenticated user.
        activities_by_id = {
            activity.activity_id: activity
            for activity in self._activity_service.get_recent(
                owner_user_id=owner_user_id,
                limit=50,
            )
        }

        # Owned Data Models are automatically visible to the user.
        owned_models = self._data_model_repository.get_by_owner_user_id(
            owner_user_id=owner_user_id,
        )

        visible_data_model_ids = {
            data_model.data_model_id
            for data_model in owned_models
        }

        # Shared Data Models are visible through Contributor/Viewer access.
        access_records = self._data_model_access_repository.get_by_user_id(
            user_id=owner_user_id,
        )

        for access in access_records:
            data_model = self._data_model_repository.get_by_id_any(
                data_model_id=access.data_model_id,
            )

            if data_model is not None:
                visible_data_model_ids.add(
                    data_model.data_model_id,
                )

        # Add all activity belonging to visible Data Models.
        for data_model_id in visible_data_model_ids:
            for activity in self._activity_service.get_by_data_model_id(
                data_model_id=data_model_id,
                limit=50,
            ):
                activities_by_id[activity.activity_id] = activity

        activities = sorted(
            activities_by_id.values(),
            key=lambda activity: activity.timestamp,
            reverse=True,
        )[:10]

        return [
            self._to_workspace_activity(
                activity=activity,
                viewer_user_id=owner_user_id,
            )
            for activity in activities
        ]

    def _to_workspace_activity(

        self,
        activity: Activity,
        viewer_user_id: str,
    ) -> WorkspaceActivity:
        try:
            activity_type = ActivityType(activity.type)
        except ValueError:
            activity_type = ActivityType.USER_SIGNED_IN

        presentation = ACTIVITY_PRESENTATION[activity_type]

        data_model = "FORGE"

        if activity.data_model_id:
            data_model_entity = self._data_model_repository.get_by_id_any(
                data_model_id=activity.data_model_id,
            )

            if data_model_entity is not None:
                data_model = data_model_entity.name
            elif activity.metadata:
                historical_name = activity.metadata.get("data_model_name")

                if isinstance(historical_name, str) and historical_name.strip():
                    data_model = historical_name

        actor_name = "FORGE"
        actor = self._user_repository.get_by_id(
            user_id=activity.actor_user_id,
        )

        if actor is not None:
            actor_name = (
                "You"
                if actor.user_id == viewer_user_id
                else actor.display_name
            )

        target_name: str | None = None

        if activity.metadata:
            target_user_id = activity.metadata.get("target_user_id")

            if isinstance(target_user_id, str) and target_user_id.strip():
                target_user = self._user_repository.get_by_id(
                    user_id=target_user_id,
                )

                if target_user is not None:
                    target_name = target_user.display_name

        description = self._build_activity_description(
            activity=activity,
            actor_name=actor_name,
            target_name=target_name,
            data_model=data_model,
        )

        return WorkspaceActivity(
            action=activity.title,
            description=description,
            data_model=data_model,
            actor=actor_name,
            target=target_name,
            time=activity.timestamp.isoformat(),
            icon=presentation.icon,
            accent=presentation.accent,
        )

    @staticmethod
    def _build_activity_description(
        activity: Activity,
        actor_name: str,
        target_name: str | None,
        data_model: str,
    ) -> str:
        """Build a human-readable Workspace activity description."""

        activity_type = ActivityType(activity.type)
        metadata = activity.metadata or {}

        if activity_type == ActivityType.DATA_MODEL_CREATED:
            return f"{actor_name} created '{data_model}'"

        if activity_type == ActivityType.DATA_MODEL_DELETED:
            return f"{actor_name} deleted '{data_model}'"

        if activity_type == ActivityType.DATA_MODEL_UPDATED:
            changes = metadata.get("changes", [])

            if isinstance(changes, list) and len(changes) == 1:
                change = changes[0]

                if isinstance(change, dict):
                    field = change.get("field")

                    if field == "name":
                        previous_name = change.get("from")
                        new_name = change.get("to")

                        if isinstance(previous_name, str) and isinstance(
                            new_name,
                            str,
                        ):
                            return (
                                f"{actor_name} renamed "
                                f"'{previous_name}' to '{new_name}'"
                            )

                    if field == "description":
                        return (
                            f"{actor_name} updated the description "
                            f"of '{data_model}'"
                        )

                    if field == "color":
                        return (
                            f"{actor_name} changed the appearance "
                            f"of '{data_model}'"
                        )

                    if field == "tags":
                        previous_tags = {
                            str(tag).lower(): str(tag)
                            for tag in change.get("from", [])
                        }
                        current_tags = {
                            str(tag).lower(): str(tag)
                            for tag in change.get("to", [])
                        }

                        added_tags = [
                            current_tags[key]
                            for key in current_tags
                            if key not in previous_tags
                        ]
                        removed_tags = [
                            previous_tags[key]
                            for key in previous_tags
                            if key not in current_tags
                        ]

                        if added_tags and removed_tags:
                            return (
                                f"{actor_name} updated tags for "
                                f"'{data_model}': added "
                                f"{', '.join(repr(tag) for tag in added_tags)} "
                                f"and removed "
                                f"{', '.join(repr(tag) for tag in removed_tags)}"
                            )

                        if added_tags:
                            return (
                                f"{actor_name} added "
                                f"{', '.join(repr(tag) for tag in added_tags)} "
                                f"to '{data_model}'"
                            )

                        if removed_tags:
                            return (
                                f"{actor_name} removed "
                                f"{', '.join(repr(tag) for tag in removed_tags)} "
                                f"from '{data_model}'"
                            )

            if isinstance(changes, list) and changes:
                fields = [
                    str(change.get("field"))
                    for change in changes
                    if isinstance(change, dict) and change.get("field")
                ]

                field_labels = {
                    "name": "name",
                    "description": "description",
                    "color": "appearance",
                    "tags": "tags",
                }

                labels = [
                    field_labels.get(field, field)
                    for field in fields
                ]

                if len(labels) == 2:
                    changed_summary = f"{labels[0]} and {labels[1]}"
                elif len(labels) > 2:
                    changed_summary = (
                        ", ".join(labels[:-1])
                        + f", and {labels[-1]}"
                    )
                elif labels:
                    changed_summary = labels[0]
                else:
                    changed_summary = "details"

                return (
                    f"{actor_name} updated {changed_summary} "
                    f"for '{data_model}'"
                )

            return f"{actor_name} updated '{data_model}'"

        if activity_type == ActivityType.DATA_MODEL_ACCESS_GRANTED:
            role = metadata.get("role", "VIEWER")
            role_label = str(role).capitalize()

            if target_name:
                return (
                    f"{actor_name} shared '{data_model}' with "
                    f"{target_name} as {role_label}"
                )

            return (
                f"{actor_name} granted {role_label} access "
                f"to '{data_model}'"
            )

        if activity_type == ActivityType.DATA_MODEL_ACCESS_ROLE_CHANGED:
            previous_role = metadata.get("from_role")
            new_role = metadata.get("to_role")

            if target_name and previous_role and new_role:
                return (
                    f"{actor_name} changed {target_name}'s access to "
                    f"'{data_model}' from "
                    f"{str(previous_role).capitalize()} to "
                    f"{str(new_role).capitalize()}"
                )

            if target_name and new_role:
                return (
                    f"{actor_name} changed {target_name}'s access to "
                    f"'{data_model}' to "
                    f"{str(new_role).capitalize()}"
                )

            return f"{actor_name} changed access to '{data_model}'"

        if activity_type == ActivityType.DATA_MODEL_ACCESS_REVOKED:
            if target_name:
                return (
                    f"{actor_name} removed {target_name}'s access "
                    f"to '{data_model}'"
                )

            return f"{actor_name} revoked access to '{data_model}'"

        if activity_type == ActivityType.USER_SIGNED_IN:
            return f"{actor_name} signed in to FORGE"

        return activity.description
