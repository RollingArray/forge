"""
File: data_model_access_service.py
Purpose: Authorization service for FORGE data model collaboration.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from app.constants.data_model_access import DataModelAccessRole
from app.interfaces.data_model_access import DataModelAccess
from app.constants.data_model_permissions import (
    DATA_MODEL_ROLE_PERMISSIONS,
    DataModelPermission,
)
from app.interfaces.data_model_access_repository import (
    DataModelAccessRepository,
)
from app.interfaces.data_model_repository import DataModelRepository
from app.repositories.json_data_model_access_repository import (
    JsonDataModelAccessRepository,
)
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)


class DataModelAccessService:
    """Determine user permissions for FORGE data models."""

    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
        access_repository: DataModelAccessRepository | None = None,
    ) -> None:
        self._data_model_repository = (
            data_model_repository
            if data_model_repository is not None
            else JsonDataModelRepository()
        )
        self._access_repository = (
            access_repository
            if access_repository is not None
            else JsonDataModelAccessRepository()
        )

    def is_owner(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether the specified user owns the data model."""

        data_model = self._data_model_repository.get_by_id(
            data_model_id=data_model_id,
            owner_user_id=user_id,
        )

        return data_model is not None

    def has_permission(
        self,
        data_model_id: str,
        user_id: str,
        permission: DataModelPermission,
    ) -> bool:
        """Return whether a user has the specified permission."""

        if self.is_owner(
            data_model_id=data_model_id,
            user_id=user_id,
        ):
            return True

        access = self._access_repository.get_access(
            data_model_id=data_model_id,
            user_id=user_id,
        )

        if access is None:
            return False

        return permission in DATA_MODEL_ROLE_PERMISSIONS.get(
            access.role,
            frozenset(),
        )

    def can_view(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether a user can view the data model."""

        return self.has_permission(
            data_model_id=data_model_id,
            user_id=user_id,
            permission=DataModelPermission.VIEW,
        )

    def can_edit(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether a user can edit the data model."""

        return self.has_permission(
            data_model_id=data_model_id,
            user_id=user_id,
            permission=DataModelPermission.EDIT,
        )

    def can_validate(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether a user can validate the data model."""

        return self.has_permission(
            data_model_id=data_model_id,
            user_id=user_id,
            permission=DataModelPermission.VALIDATE,
        )

    def can_generate(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether a user can generate data."""

        return self.has_permission(
            data_model_id=data_model_id,
            user_id=user_id,
            permission=DataModelPermission.GENERATE,
        )

    def can_view_results(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether a user can view generation results."""

        return self.has_permission(
            data_model_id=data_model_id,
            user_id=user_id,
            permission=DataModelPermission.VIEW_RESULTS,
        )

    def can_export(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether a user can export generated data."""

        return self.has_permission(
            data_model_id=data_model_id,
            user_id=user_id,
            permission=DataModelPermission.EXPORT,
        )

    def can_share(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether a user can share the data model."""

        return self.is_owner(
            data_model_id=data_model_id,
            user_id=user_id,
        )

    def can_manage_access(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether a user can manage model access."""

        return self.is_owner(
            data_model_id=data_model_id,
            user_id=user_id,
        )

    def can_delete(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Return whether a user can delete the data model."""

        return self.is_owner(
            data_model_id=data_model_id,
            user_id=user_id,
        )

    def grant_access(
        self,
        data_model_id: str,
        owner_user_id: str,
        target_user_id: str,
        role: DataModelAccessRole,
    ) -> DataModelAccess | None:
        """Grant or update access for an existing FORGE user."""

        if not self.can_manage_access(
            data_model_id=data_model_id,
            user_id=owner_user_id,
        ):
            return None

        return self._access_repository.grant_access(
            data_model_id=data_model_id,
            user_id=target_user_id,
            role=role,
        )

    def update_role(
        self,
        data_model_id: str,
        owner_user_id: str,
        target_user_id: str,
        role: DataModelAccessRole,
    ) -> DataModelAccess | None:
        """Update an existing user's access role when called by the owner."""

        if not self.can_manage_access(
            data_model_id=data_model_id,
            user_id=owner_user_id,
        ):
            return None

        if target_user_id == owner_user_id:
            return None

        return self._access_repository.update_role(
            data_model_id=data_model_id,
            user_id=target_user_id,
            role=role,
        )

    def get_access(
        self,
        data_model_id: str,
        user_id: str,
    ) -> list[DataModelAccess] | None:
        """Return access records when the user can view the data model."""

        if not self.can_view(
            data_model_id=data_model_id,
            user_id=user_id,
        ):
            return None

        return self._access_repository.get_by_data_model_id(
            data_model_id=data_model_id,
        )

    def revoke_access(
        self,
        data_model_id: str,
        owner_user_id: str,
        target_user_id: str,
    ) -> bool:
        """Revoke an existing user's access when called by the owner."""

        if not self.can_manage_access(
            data_model_id=data_model_id,
            user_id=owner_user_id,
        ):
            return False

        if target_user_id == owner_user_id:
            return False

        return self._access_repository.revoke_access(
            data_model_id=data_model_id,
            user_id=target_user_id,
        )

    def get_role(
        self,
        data_model_id: str,
        user_id: str,
    ) -> str | None:
        """Return the effective role for a user."""

        if self.is_owner(
            data_model_id=data_model_id,
            user_id=user_id,
        ):
            return "OWNER"

        access = self._access_repository.get_access(
            data_model_id=data_model_id,
            user_id=user_id,
        )

        if access is None:
            return None

        return access.role.value
