"""
File: data_model_permissions.py
Purpose: Permission definitions for FORGE data model collaboration.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from enum import StrEnum


class DataModelPermission(StrEnum):
    """Capabilities that can be granted through data model access."""

    VIEW = "VIEW"
    EDIT = "EDIT"
    VALIDATE = "VALIDATE"
    GENERATE = "GENERATE"
    VIEW_RESULTS = "VIEW_RESULTS"
    EXPORT = "EXPORT"
    SHARE = "SHARE"
    MANAGE_ACCESS = "MANAGE_ACCESS"
    DELETE = "DELETE"


from app.constants.data_model_access import DataModelAccessRole


DATA_MODEL_ROLE_PERMISSIONS: dict[
    DataModelAccessRole,
    frozenset[DataModelPermission],
] = {
    DataModelAccessRole.CONTRIBUTOR: frozenset(
        {
            DataModelPermission.VIEW,
            DataModelPermission.EDIT,
            DataModelPermission.VALIDATE,
            DataModelPermission.GENERATE,
            DataModelPermission.VIEW_RESULTS,
            DataModelPermission.EXPORT,
        }
    ),
    DataModelAccessRole.VIEWER: frozenset(
        {
            DataModelPermission.VIEW,
            DataModelPermission.VIEW_RESULTS,
            DataModelPermission.EXPORT,
        }
    ),
}
