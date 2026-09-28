"""
File: specification.py
Purpose: FORGE model specification API endpoints.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.models.population_model import (
    AcceptPopulationPlanRequest,
    PopulationTargetRequest,
)
from app.models.specification_entity_model import (
    CreateEntityRequest,
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
from app.services.data_model_access_service import DataModelAccessService
from app.services.population_service import PopulationService
from app.services.specification_service import SpecificationService
from app.services.specification_validation_service import SpecificationValidationService


router = APIRouter(
    prefix="/data-models",
    tags=["Specifications"],
)

population_service = PopulationService()
specification_service = SpecificationService()
specification_validation_service = SpecificationValidationService()
data_model_access_service = DataModelAccessService()


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

    return specification_validation_service.validate(specification)


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
