"""
File: specification.py
Purpose: FORGE model specification API endpoints.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.models.population_model import (
    AcceptPopulationPlanRequest,
    PopulationTargetRequest,
)
from app.models.specification_entity_model import (
    CreateEntityRequest,
    UpdateEntityRequest,
    UpdateEntityIdentityRequest,
    UpdateEntityPopulationRequest,
    UpdateEntityPopulationScalingRequest,
)
from app.models.specification_field_model import (
    CreateFieldRequest,
    UpdateFieldRequest,
)
from app.models.specification_constraint_model import (
    CreateConstraintRequest,
    UpdateConstraintRequest,
    DeleteConstraintRequest,
)
from app.models.specification_relationship_model import (
    CreateRelationshipRequest,
    DeleteRelationshipRequest,
    UpdateRelationshipRequest,
)
from app.models.specification_foreign_key_model import (
    CreateForeignKeyRequest,
    ExistingForeignKeyRequest,
    UpdateForeignKeyRequest,
)
from app.models.specification_model import SpecificationModel
from app.models.specification_import_model import (
    SpecificationImportPreviewRequest,
    SpecificationImportPreviewResponse,
    SpecificationImportApplyRequest,
    SpecificationImportApplyResponse,
)
from app.services.data_model_access_service import DataModelAccessService
from app.services.activity_service import ActivityService
from app.constants.activity import ActivityType
from app.repositories.json_data_model_repository import JsonDataModelRepository
from app.repositories.json_specification_repository import (
    JsonSpecificationRepository,
    SpecificationRevisionConflict,
)
from app.services.population_service import PopulationService
from app.services.specification_service import SpecificationService
from app.services.specification_validation_service import SpecificationValidationService
from app.services.specification_import_service import SpecificationImportService


router = APIRouter(
    prefix="/data-models",
    tags=["Specifications"],
)

population_service = PopulationService()
specification_service = SpecificationService()
specification_validation_service = SpecificationValidationService()
data_model_access_service = DataModelAccessService()
activity_service = ActivityService()
data_model_repository = JsonDataModelRepository()
specification_import_service = SpecificationImportService()
specification_import_repository = JsonSpecificationRepository()




@router.get(
    "/{data_model_id}/specification",
    response_model=SpecificationModel,
    status_code=status.HTTP_200_OK,
)
async def get_specification(
    data_model_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> SpecificationModel:
    """Return the canonical FORGE specification for a visible Data Model."""

    if not data_model_access_service.can_view(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    specification = specification_service.get_specification(
        data_model_id=data_model_id,
    )

    if specification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return SpecificationModel(**specification)


@router.put(
    "/{data_model_id}/specification",
    response_model=SpecificationModel,
    status_code=status.HTTP_200_OK,
)
async def save_specification(
    data_model_id: str,
    request: SpecificationModel,
    user: AuthUser = Depends(get_authenticated_user),
) -> SpecificationModel:
    """Validate and persist a reviewed canonical specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    candidate = request.model_dump(mode="python")

    # Semantic validation is available separately. Persist structurally valid
    # specifications so users can correct semantic findings in Model Studio.
    saved = specification_service.save_specification(
        data_model_id=data_model_id,
        specification=candidate,
    )

    if saved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    data_model = data_model_repository.get_by_id_any(
        data_model_id=data_model_id,
    )
    if data_model is not None:
        activity_service.record(
            owner_user_id=data_model.owner_user_id,
            actor_user_id=user.user_id,
            activity_type=ActivityType.AI_PROPOSAL_ACCEPTED,
            title="Specification saved",
            description="A reviewed specification was validated and saved.",
            data_model_id=data_model_id,
        )

    return SpecificationModel(**saved)


@router.get(
    "/{data_model_id}/specification/validation",
    status_code=status.HTTP_200_OK,
)
async def validate_specification(
    data_model_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Validate the canonical FORGE specification for a visible Data Model."""

    if not data_model_access_service.can_view(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    specification = specification_service.get_specification(
        data_model_id=data_model_id,
    )

    if specification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    result = specification_validation_service.validate(specification)
    data_model = data_model_repository.get_by_id_any(
        data_model_id=data_model_id,
    )
    if data_model is not None:
        findings = result.get("findings", [])
        failed = not result.get("can_continue", False)
        activity_service.record(
            owner_user_id=data_model.owner_user_id,
            actor_user_id=user.user_id,
            activity_type=(
                ActivityType.MODEL_VALIDATION_FAILED
                if failed
                else ActivityType.MODEL_VALIDATED
            ),
            title=(
                "Specification validation failed"
                if failed
                else "Specification validated"
            ),
            description=(
                f"Validation completed with {len(findings)} finding(s)."
            ),
            data_model_id=data_model_id,
        )
    return result


@router.get(
    "/{data_model_id}/population-plan",
    status_code=status.HTTP_200_OK,
)
async def get_population_plan(
    data_model_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Return the population plan for a visible Data Model."""

    if not data_model_access_service.can_view(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    population_plan = population_service.get_population_plan(
        data_model_id=data_model_id,
    )

    if population_plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return population_plan


@router.post(
    "/{data_model_id}/population-plan/candidate",
    status_code=status.HTTP_200_OK,
)
async def build_population_candidate(
    data_model_id: str,
    request: PopulationTargetRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Build and evaluate a target-driven candidate population plan."""

    if not data_model_access_service.can_view(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    candidate = population_service.build_candidate_plan(
        data_model_id=data_model_id,
        target=request.target,
        driver=request.driver,
    )

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return candidate


@router.post(
    "/{data_model_id}/population-plan/accept",
    status_code=status.HTTP_200_OK,
)
async def accept_population_plan(
    data_model_id: str,
    request: AcceptPopulationPlanRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Accept and persist the population plan for generation."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        specification = specification_service.accept_population_plan(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            populations=request.populations,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if specification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return specification


@router.post(
    "/{data_model_id}/specification/entities",
    status_code=status.HTTP_201_CREATED,
)
async def create_entity(
    data_model_id: str,
    request: CreateEntityRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Create an entity in the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        entity = specification_service.create_entity(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return entity


@router.put(
    "/{data_model_id}/specification/entities/{entity_name}",
    status_code=status.HTTP_200_OK,
)
async def update_entity(
    data_model_id: str,
    entity_name: str,
    request: UpdateEntityRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Update the editable details of an existing FORGE entity."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        entity = specification_service.update_entity(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return entity


@router.put(
    "/{data_model_id}/specification/entities/{entity_name}/identity",
    status_code=status.HTTP_200_OK,
)
async def update_entity_identity(
    data_model_id: str,
    entity_name: str,
    request: UpdateEntityIdentityRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Define the identity fields for an existing FORGE entity."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        entity = specification_service.update_entity_identity(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            fields=request.fields,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return entity


@router.post(
    "/{data_model_id}/specification/entities/{entity_name}/fields",
    status_code=status.HTTP_201_CREATED,
)
async def create_field(
    data_model_id: str,
    entity_name: str,
    request: CreateFieldRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Create a field in an existing FORGE entity."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        field = specification_service.create_field(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return field


@router.put(
    "/{data_model_id}/specification/entities/{entity_name}/fields/{field_name}",
    status_code=status.HTTP_200_OK,
)
async def update_field(
    data_model_id: str,
    entity_name: str,
    field_name: str,
    request: UpdateFieldRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Update an existing field in a FORGE entity."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        field = specification_service.update_field(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            field_name=field_name,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return field


@router.delete(
    "/{data_model_id}/specification/entities/{entity_name}/fields/{field_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_field(
    data_model_id: str,
    entity_name: str,
    field_name: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Delete a field that has no remaining specification dependencies."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        field = specification_service.delete_field(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            field_name=field_name,
        )
    except ValueError as exc:
        detail = str(exc)
        code = (
            status.HTTP_409_CONFLICT
            if detail.startswith("Cannot delete field")
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=code, detail=detail) from exc

    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )


@router.put(
    "/{data_model_id}/specification/entities/{entity_name}/population/scaling",
    status_code=status.HTTP_200_OK,
)
async def update_entity_population_scaling(
    data_model_id: str,
    entity_name: str,
    request: UpdateEntityPopulationScalingRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Update the population scaling of an existing FORGE entity."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        entity = specification_service.update_entity_population_scaling(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            scaling=request.scaling.value,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return entity


@router.put(
    "/{data_model_id}/specification/entities/{entity_name}/population",
    status_code=status.HTTP_200_OK,
)
async def update_entity_population(
    data_model_id: str,
    entity_name: str,
    request: UpdateEntityPopulationRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Update the population of an existing FORGE entity."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        entity = specification_service.update_entity_population(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            count=request.count,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return entity


@router.post(
    "/{data_model_id}/specification/foreign-keys",
    status_code=status.HTTP_201_CREATED,
)
async def create_foreign_key(
    data_model_id: str,
    request: CreateForeignKeyRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Create a deterministic foreign key in the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        foreign_key = specification_service.create_foreign_key(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if foreign_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return foreign_key


@router.put(
    "/{data_model_id}/specification/foreign-keys",
)
async def update_foreign_key(
    data_model_id: str,
    request: UpdateForeignKeyRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Update a deterministic foreign key in the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        foreign_key = specification_service.update_foreign_key(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if foreign_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return foreign_key


@router.delete(
    "/{data_model_id}/specification/foreign-keys",
)
async def delete_foreign_key(
    data_model_id: str,
    request: ExistingForeignKeyRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Delete a deterministic foreign key from the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        foreign_key = specification_service.delete_foreign_key(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if foreign_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return foreign_key


@router.post(
    "/{data_model_id}/specification/relationships",
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    data_model_id: str,
    request: CreateRelationshipRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Create a relationship in the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        relationship = specification_service.create_relationship(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return relationship



@router.post(
    "/{data_model_id}/specification/constraints",
    status_code=status.HTTP_201_CREATED,
)
async def create_constraint(
    data_model_id: str,
    request: CreateConstraintRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Create a deterministic constraint in a FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        constraint = specification_service.create_constraint(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if constraint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return constraint


@router.put(
    "/{data_model_id}/specification/constraints",
    status_code=status.HTTP_200_OK,
)
async def update_constraint(
    data_model_id: str,
    request: UpdateConstraintRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Update a deterministic constraint."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        constraint = specification_service.update_constraint(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if constraint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return constraint


@router.delete(
    "/{data_model_id}/specification/constraints",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_constraint(
    data_model_id: str,
    request: DeleteConstraintRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Delete a deterministic constraint."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    deleted = specification_service.delete_constraint(
        data_model_id=data_model_id,
        actor_user_id=user.user_id,
        request=request.model_dump(),
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Constraint not found.",
        )


@router.put(
    "/{data_model_id}/specification/relationships",
    status_code=status.HTTP_200_OK,
)
async def update_relationship(
    data_model_id: str,
    request: UpdateRelationshipRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Update an existing relationship in the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        relationship = specification_service.update_relationship(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            existing_relationship=request.existing.model_dump(),
            request=request.relationship,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if relationship is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return relationship


@router.delete(
    "/{data_model_id}/specification/relationships",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_relationship(
    data_model_id: str,
    request: DeleteRelationshipRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Delete a relationship from the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    relationship = request.model_dump()

    try:
        deleted = specification_service.delete_relationship(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            relationship=relationship,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found.",
        )


@router.delete(
    "/{data_model_id}/specification/entities/{entity_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_entity(
    data_model_id: str,
    entity_name: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Delete an entity from the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        deleted = specification_service.delete_entity(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found.",
        )


@router.post(
    "/{data_model_id}/specification/import/preview",
    response_model=SpecificationImportPreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def specification_import_preview(
    data_model_id: str,
    request: SpecificationImportPreviewRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> SpecificationImportPreviewResponse:
    """Preview additive CSV changes without modifying the specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    data_model = data_model_repository.get_by_id_any(
        data_model_id=data_model_id,
    )
    if data_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    csv_sections = request.csv.model_dump()
    parsed = specification_import_service.parse_and_convert(csv_sections)

    existing = specification_import_repository.read(data_model_id)
    baseline = (
        existing
        if existing is not None
        else specification_import_repository._create_empty_specification(
            model_name=data_model.name,
            model_description=data_model.description,
        )
    )

    merged = specification_import_service.merge_into_specification(
        existing_specification=baseline,
        parsed_result=parsed,
    )

    canonical_csv = json.dumps(
        csv_sections,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    csv_digest = hashlib.sha256(canonical_csv).hexdigest()

    return SpecificationImportPreviewResponse(
        base_revision=specification_import_repository.revision(baseline),
        csv_digest=csv_digest,
        can_apply=merged["can_apply"],
        summary=merged["summary"],
        sections=parsed["sections"],
        additions=merged["additions"],
        already_present=merged["already_present"],
        conflicts=merged["conflicts"],
        issues=merged["issues"],
    )


@router.post(
    "/{data_model_id}/specification/import/apply",
    response_model=SpecificationImportApplyResponse,
    status_code=status.HTTP_200_OK,
)
async def specification_import_apply(
    data_model_id: str,
    request: SpecificationImportApplyRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> SpecificationImportApplyResponse:
    """Apply the exact reviewed CSV against the reviewed specification revision."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    data_model = data_model_repository.get_by_id_any(
        data_model_id=data_model_id,
    )
    if data_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    csv_sections = request.csv.model_dump()
    canonical_csv = json.dumps(
        csv_sections,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    actual_digest = hashlib.sha256(canonical_csv).hexdigest()

    if actual_digest != request.csv_digest:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The CSV content differs from the reviewed preview.",
        )

    try:
        with specification_import_repository.transaction(data_model_id):
            existing = specification_import_repository.read(data_model_id)
            baseline = (
                existing
                if existing is not None
                else specification_import_repository._create_empty_specification(
                    model_name=data_model.name,
                    model_description=data_model.description,
                )
            )

            current_revision = specification_import_repository.revision(
                baseline
            )
            if current_revision != request.base_revision:
                raise SpecificationRevisionConflict(
                    "The specification changed after preview. "
                    "Refresh the preview before applying the import."
                )

            parsed = specification_import_service.parse_and_convert(
                csv_sections
            )
            merged = specification_import_service.merge_into_specification(
                existing_specification=baseline,
                parsed_result=parsed,
            )

            if not merged["can_apply"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "message": "The CSV import contains conflicts or validation issues.",
                        "summary": merged["summary"],
                        "conflicts": merged["conflicts"],
                        "issues": merged["issues"],
                    },
                )

            if merged["additions"]:
                saved = specification_import_repository.save_if_revision(
                    data_model_id=data_model_id,
                    expected_revision=request.base_revision,
                    specification=merged["candidate"],
                    missing_specification=(
                        baseline if existing is None else None
                    ),
                )
            else:
                saved = baseline

            resulting_revision = specification_import_repository.revision(
                saved
            )

    except SpecificationRevisionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if merged["additions"]:
        activity_service.record(
            owner_user_id=data_model.owner_user_id,
            actor_user_id=user.user_id,
            activity_type=ActivityType.SPECIFICATION_IMPORT_APPLIED,
            title="Specification imported",
            description=(
                f"CSV import added {len(merged['additions'])} "
                "specification definitions."
            ),
            data_model_id=data_model_id,
            metadata=merged["summary"],
        )

    return SpecificationImportApplyResponse(
        applied=True,
        summary=merged["summary"],
        specification_revision=resulting_revision,
    )
