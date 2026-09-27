"""
File: specification_service.py
Purpose: Business service for FORGE model specifications.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.interfaces.data_model_repository import DataModelRepository
from app.interfaces.specification_repository import SpecificationRepository
from app.models.specification_entity_model import CreateEntityRequest
from app.models.specification_field_model import (
    CreateFieldRequest,
    UpdateFieldRequest,
)
from app.models.specification_constraint_model import (
    CreateConstraintRequest,
    UpdateConstraintRequest,
)
from app.models.specification_relationship_model import (
    CreateRelationshipRequest,
)
from app.constants.activity import ActivityType
from app.services.activity_service import ActivityService
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)
from app.repositories.json_specification_repository import (
    JsonSpecificationRepository,
)


class SpecificationService:
    """Provide business operations for FORGE specifications."""

    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
        specification_repository: SpecificationRepository | None = None,
        activity_service: ActivityService | None = None,
    ) -> None:
        self._data_model_repository = (
            data_model_repository
            if data_model_repository is not None
            else JsonDataModelRepository()
        )
        self._specification_repository = (
            specification_repository
            if specification_repository is not None
            else JsonSpecificationRepository()
        )
        self._activity_service = (
            activity_service
            if activity_service is not None
            else ActivityService()
        )

    def get_specification(
        self,
        data_model_id: str,
    ) -> dict[str, Any] | None:
        """Return the canonical specification for a Data Model."""

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is None:
            return None

        return self._specification_repository.get_or_create(
            data_model_id=data_model_id,
            model_name=data_model.name,
            model_description=data_model.description,
        )

    def create_entity(
        self,
        data_model_id: str,
        actor_user_id: str,
        request: CreateEntityRequest,
    ) -> dict[str, Any] | None:
        """Create and persist an entity in the canonical specification."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        entities = specification.setdefault(
            "entities",
            [],
        )

        if any(
            entity.get("name") == request.name
            for entity in entities
        ):
            raise ValueError(
                f"Entity already exists: {request.name}"
            )

        entity: dict[str, Any] = {
            "name": request.name,
            "fields": [],
        }

        if request.population is not None:
            entity["population"] = {
                "count": request.population.count,
            }
        else:
            entity["population"] = {}

        candidate = deepcopy(specification)
        candidate["entities"].append(entity)

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.ENTITY_ADDED,
                title="Entity added",
                description=f"Added entity '{request.name}'",
                data_model_id=data_model_id,
                metadata={
                    "entity_name": request.name,
                    "population": (
                        request.population.count
                        if request.population is not None
                        else None
                    ),
                },
            )

        return entity



    def update_entity_identity(
        self,
        data_model_id: str,
        actor_user_id: str,
        entity_name: str,
        fields: list[str],
    ) -> dict[str, Any] | None:
        """Define the identity fields for an existing entity."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        entity = next(
            (
                item
                for item in specification.get("entities", [])
                if item.get("name") == entity_name
            ),
            None,
        )

        if entity is None:
            raise ValueError(
                f"Unknown entity: {entity_name}"
            )

        entity_fields = {
            field.get("name")
            for field in entity.get("fields", [])
        }

        unknown_fields = [
            field
            for field in fields
            if field not in entity_fields
        ]

        if unknown_fields:
            raise ValueError(
                "Unknown identity field(s): "
                + ", ".join(unknown_fields)
            )

        candidate = deepcopy(specification)

        candidate_entity = next(
            item
            for item in candidate["entities"]
            if item.get("name") == entity_name
        )

        candidate_entity["identity"] = {
            "fields": list(fields),
        }

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.ENTITY_UPDATED,
                title="Entity identity updated",
                description=(
                    f"Updated identity for entity "
                    f"'{entity_name}'"
                ),
                data_model_id=data_model_id,
                metadata={
                    "entity_name": entity_name,
                    "identity_fields": list(fields),
                    "composite": len(fields) > 1,
                },
            )

        return candidate_entity

    def create_field(
        self,
        data_model_id: str,
        actor_user_id: str,
        entity_name: str,
        request: CreateFieldRequest,
    ) -> dict[str, Any] | None:
        """Create and persist a field in an existing entity."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        entities = specification.setdefault(
            "entities",
            [],
        )

        entity = next(
            (
                item
                for item in entities
                if item.get("name") == entity_name
            ),
            None,
        )

        if entity is None:
            raise ValueError(
                f"Unknown entity: {entity_name}"
            )

        fields = entity.setdefault(
            "fields",
            [],
        )

        if any(
            field.get("name") == request.name
            for field in fields
        ):
            raise ValueError(
                f"Field already exists: {entity_name}.{request.name}"
            )

        field: dict[str, Any] = {
            "name": request.name,
            "type": request.type,
        }

        if request.identity is not None:
            field["identity"] = request.identity.model_dump(
                exclude_none=True,
            )

        if request.generation is not None:
            field["generation"] = request.generation.model_dump(
                exclude_none=True,
            )

        candidate = deepcopy(specification)

        candidate_entity = next(
            item
            for item in candidate["entities"]
            if item.get("name") == entity_name
        )

        candidate_entity.setdefault(
            "fields",
            [],
        ).append(field)

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.FIELD_ADDED,
                title="Field added",
                description=(
                    f"Added field '{entity_name}.{request.name}'"
                ),
                data_model_id=data_model_id,
                metadata={
                    "entity_name": entity_name,
                    "field_name": request.name,
                    "field_type": request.type,
                },
            )

        return field

    def update_field(
        self,
        data_model_id: str,
        actor_user_id: str,
        entity_name: str,
        field_name: str,
        request: UpdateFieldRequest,
    ) -> dict[str, Any] | None:
        """Update an existing field in the canonical specification."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        entity = next(
            (
                item
                for item in specification.get("entities", [])
                if item.get("name") == entity_name
            ),
            None,
        )

        if entity is None:
            raise ValueError(
                f"Unknown entity: {entity_name}"
            )

        field = next(
            (
                item
                for item in entity.get("fields", [])
                if item.get("name") == field_name
            ),
            None,
        )

        if field is None:
            raise ValueError(
                f"Unknown field: {entity_name}.{field_name}"
            )

        updates = request.model_dump(
            exclude_unset=True,
        )

        candidate = deepcopy(specification)

        candidate_entity = next(
            item
            for item in candidate["entities"]
            if item.get("name") == entity_name
        )

        candidate_field = next(
            item
            for item in candidate_entity.get("fields", [])
            if item.get("name") == field_name
        )

        for key, value in updates.items():
            if key in {"identity", "generation"} and value is not None:
                value = value.model_dump(
                    exclude_none=True,
                ) if hasattr(value, "model_dump") else value

            candidate_field[key] = value

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.FIELD_UPDATED,
                title="Field updated",
                description=(
                    f"Updated field '{entity_name}.{field_name}'"
                ),
                data_model_id=data_model_id,
                metadata={
                    "entity_name": entity_name,
                    "field_name": field_name,
                    "updates": list(updates.keys()),
                },
            )

        return candidate_field

    def update_entity_population(
        self,
        data_model_id: str,
        actor_user_id: str,
        entity_name: str,
        count: int,
    ) -> dict[str, Any] | None:
        """Update an entity population using UPDATE_POPULATION semantics."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        entities = specification.setdefault("entities", [])

        entity = next(
            (
                item
                for item in entities
                if item.get("name") == entity_name
            ),
            None,
        )

        if entity is None:
            raise ValueError(
                f"Unknown entity: {entity_name}"
            )

        candidate = deepcopy(specification)

        updated_entity = next(
            item
            for item in candidate["entities"]
            if item.get("name") == entity_name
        )

        updated_entity["population"] = {
            "count": count,
        }

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.ENTITY_UPDATED,
                title="Entity updated",
                description=(
                    f"Updated population for entity '{entity_name}'"
                ),
                data_model_id=data_model_id,
                metadata={
                    "entity_name": entity_name,
                    "operation": "UPDATE_POPULATION",
                    "population": count,
                },
            )

        return updated_entity

    def create_relationship(
        self,
        data_model_id: str,
        actor_user_id: str,
        request: CreateRelationshipRequest,
    ) -> dict[str, Any] | None:
        """Create a relationship using an existing compatible foreign key."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        entities = specification.get("entities", [])

        source_entity = next(
            (
                entity
                for entity in entities
                if entity.get("name") == request.source_entity
            ),
            None,
        )

        target_entity = next(
            (
                entity
                for entity in entities
                if entity.get("name") == request.target_entity
            ),
            None,
        )

        if source_entity is None:
            raise ValueError(
                f"Unknown source entity: {request.source_entity}"
            )

        if target_entity is None:
            raise ValueError(
                f"Unknown target entity: {request.target_entity}"
            )

        if request.source_entity == request.target_entity:
            raise ValueError(
                "A relationship must connect two different entities."
            )

        foreign_keys = specification.get("foreign_keys", [])

        compatible_foreign_keys = [
            foreign_key
            for foreign_key in foreign_keys
            if (
                foreign_key.get("source", {}).get("entity")
                == request.source_entity
                and foreign_key.get("target", {}).get("entity")
                == request.target_entity
            )
            or (
                foreign_key.get("source", {}).get("entity")
                == request.target_entity
                and foreign_key.get("target", {}).get("entity")
                == request.source_entity
            )
        ]

        if not compatible_foreign_keys:
            raise ValueError(
                f"No compatible foreign key exists between "
                f"'{request.source_entity}' and "
                f"'{request.target_entity}'. "
                "Define a foreign key first."
            )

        if len(compatible_foreign_keys) > 1:
            names = [
                foreign_key.get("name", "Unnamed foreign key")
                for foreign_key in compatible_foreign_keys
            ]

            raise ValueError(
                "Multiple foreign keys exist between "
                f"'{request.source_entity}' and "
                f"'{request.target_entity}': "
                + ", ".join(names)
                + "."
            )

        foreign_key = compatible_foreign_keys[0]

        fk_source = foreign_key.get("source", {})
        fk_target = foreign_key.get("target", {})

        fk_source_entity = fk_source.get("entity")
        fk_source_fields = fk_source.get("fields", [])

        fk_target_entity = fk_target.get("entity")
        fk_target_fields = fk_target.get("fields", [])

        if (
            not isinstance(fk_source_entity, str)
            or not isinstance(fk_target_entity, str)
            or not isinstance(fk_source_fields, list)
            or not isinstance(fk_target_fields, list)
            or not fk_source_fields
            or not fk_target_fields
        ):
            raise ValueError(
                "The compatible foreign key has an invalid structure."
            )

        if fk_source_entity == request.source_entity:
            relationship_source = (
                f"{fk_source_entity}.{fk_source_fields[0]}"
            )
            relationship_target = (
                f"{fk_target_entity}.{fk_target_fields[0]}"
            )
        else:
            relationship_source = (
                f"{fk_target_entity}.{fk_target_fields[0]}"
            )
            relationship_target = (
                f"{fk_source_entity}.{fk_source_fields[0]}"
            )

        relationship = {
            "source": relationship_source,
            "target": relationship_target,
            "type": request.type,
            "source_participation": request.source_participation,
            "target_participation": request.target_participation,
        }

        relationships = specification.setdefault(
            "relationships",
            [],
        )

        if relationship in relationships:
            raise ValueError(
                "Relationship already exists."
            )

        candidate = deepcopy(specification)
        candidate["relationships"].append(relationship)

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.RELATIONSHIP_ADDED,
                title="Relationship added",
                description=(
                    f"Added relationship "
                    f"'{relationship['source']}' → "
                    f"'{relationship['target']}'"
                ),
                data_model_id=data_model_id,
                metadata={
                    **relationship,
                    "foreign_key": foreign_key.get("name"),
                },
            )

        return relationship

    def update_relationship(
        self,
        data_model_id: str,
        actor_user_id: str,
        existing_relationship: dict[str, Any],
        request: UpdateRelationshipRequest,
    ) -> dict[str, Any] | None:
        """Update an existing relationship using an existing compatible foreign key."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        relationships = specification.get("relationships", [])

        existing = next(
            (
                relationship
                for relationship in relationships
                if relationship == existing_relationship
            ),
            None,
        )

        if existing is None:
            raise ValueError("Relationship not found.")

        if request.source_entity == request.target_entity:
            raise ValueError(
                "A relationship must connect two different entities."
            )

        entities = specification.get("entities", [])

        source_entity = next(
            (
                entity
                for entity in entities
                if entity.get("name") == request.source_entity
            ),
            None,
        )

        target_entity = next(
            (
                entity
                for entity in entities
                if entity.get("name") == request.target_entity
            ),
            None,
        )

        if source_entity is None:
            raise ValueError(
                f"Unknown source entity: {request.source_entity}"
            )

        if target_entity is None:
            raise ValueError(
                f"Unknown target entity: {request.target_entity}"
            )

        foreign_keys = specification.get("foreign_keys", [])

        compatible_foreign_keys = [
            foreign_key
            for foreign_key in foreign_keys
            if (
                foreign_key.get("source", {}).get("entity")
                == request.source_entity
                and foreign_key.get("target", {}).get("entity")
                == request.target_entity
            )
            or (
                foreign_key.get("source", {}).get("entity")
                == request.target_entity
                and foreign_key.get("target", {}).get("entity")
                == request.source_entity
            )
        ]

        if not compatible_foreign_keys:
            raise ValueError(
                f"No compatible foreign key exists between "
                f"'{request.source_entity}' and "
                f"'{request.target_entity}'. "
                "Define a foreign key first."
            )

        if len(compatible_foreign_keys) > 1:
            names = [
                foreign_key.get("name", "Unnamed foreign key")
                for foreign_key in compatible_foreign_keys
            ]

            raise ValueError(
                "Multiple compatible foreign keys exist between "
                f"'{request.source_entity}' and "
                f"'{request.target_entity}': "
                + ", ".join(names)
            )

        foreign_key = compatible_foreign_keys[0]

        fk_source = foreign_key.get("source", {})
        fk_target = foreign_key.get("target", {})

        fk_source_entity = fk_source.get("entity")
        fk_target_entity = fk_target.get("entity")

        fk_source_fields = fk_source.get("fields", [])
        fk_target_fields = fk_target.get("fields", [])

        if not fk_source_entity or not fk_target_entity:
            raise ValueError(
                "The foreign key does not define valid source and target entities."
            )

        if not fk_source_fields or not fk_target_fields:
            raise ValueError(
                "The foreign key does not define valid source and target fields."
            )

        if fk_source_entity == request.source_entity:
            relationship_source = (
                f"{fk_source_entity}.{fk_source_fields[0]}"
            )
            relationship_target = (
                f"{fk_target_entity}.{fk_target_fields[0]}"
            )
        else:
            relationship_source = (
                f"{fk_target_entity}.{fk_target_fields[0]}"
            )
            relationship_target = (
                f"{fk_source_entity}.{fk_source_fields[0]}"
            )

        updated_relationship = {
            "source": relationship_source,
            "target": relationship_target,
            "type": request.type,
            "source_participation": request.source_participation,
            "target_participation": request.target_participation,
        }

        candidate = deepcopy(specification)

        candidate["relationships"] = [
            updated_relationship
            if relationship == existing
            else relationship
            for relationship in candidate["relationships"]
        ]

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.RELATIONSHIP_UPDATED,
                title="Relationship updated",
                description=(
                    f"Updated relationship "
                    f"'{updated_relationship['source']}' → "
                    f"'{updated_relationship['target']}'"
                ),
                data_model_id=data_model_id,
                metadata={
                    "previous": existing,
                    "updated": updated_relationship,
                    "foreign_key": foreign_key.get("name"),
                },
            )

        return updated_relationship


    def delete_relationship(
        self,
        data_model_id: str,
        actor_user_id: str,
        relationship: dict[str, Any],
    ) -> bool:
        """Delete an existing relationship."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return False

        relationships = specification.get(
            "relationships",
            [],
        )

        if relationship not in relationships:
            return False

        candidate = deepcopy(specification)

        candidate["relationships"] = [
            item
            for item in candidate["relationships"]
            if item != relationship
        ]

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.RELATIONSHIP_DELETED,
                title="Relationship deleted",
                description=(
                    f"Deleted relationship "
                    f"'{relationship.get('source')}' → "
                    f"'{relationship.get('target')}'"
                ),
                data_model_id=data_model_id,
                metadata=relationship,
            )

        return True


    def _validate_constraint_compatibility(
        self,
        field: dict[str, Any],
        operator: str,
    ) -> None:
        """Validate that a constraint can be executed for a field."""

        field_type = field.get("type")

        supported_operators = {
            "INTEGER": {">", ">=", "<", "<="},
            "DECIMAL": {">", ">=", "<", "<="},
            "CATEGORICAL": {">", ">=", "<", "<=", "==", "!="},
        }

        operators = supported_operators.get(field_type)

        if operators is None:
            raise ValueError(
                f"Constraints are not supported for "
                f"{field_type} fields."
            )

        if operator not in operators:
            raise ValueError(
                f"Operator {operator!r} is not supported for "
                f"{field_type} fields."
            )

    def create_constraint(
        self,
        data_model_id: str,
        actor_user_id: str,
        request: CreateConstraintRequest,
    ) -> dict[str, Any] | None:
        """Create and persist a deterministic field constraint."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        entity = next(
            (
                item
                for item in specification.get("entities", [])
                if item.get("name") == request.entity
            ),
            None,
        )

        if entity is None:
            raise ValueError(
                f"Unknown entity: {request.entity}"
            )

        field = next(
            (
                item
                for item in entity.get("fields", [])
                if item.get("name") == request.field
            ),
            None,
        )

        if field is None:
            raise ValueError(
                f"Unknown field: {request.entity}.{request.field}"
            )

        self._validate_constraint_compatibility(
            field=field,
            operator=request.operator,
        )

        constraints = specification.setdefault(
            "constraints",
            [],
        )

        candidate_constraint = request.model_dump()

        if candidate_constraint in constraints:
            raise ValueError(
                "Constraint already exists."
            )

        candidate = deepcopy(specification)
        candidate.setdefault("constraints", []).append(
            candidate_constraint,
        )

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.CONSTRAINT_ADDED,
                title="Constraint added",
                description=(
                    f"Added constraint on "
                    f"'{request.entity}.{request.field}'"
                ),
                data_model_id=data_model_id,
                metadata=candidate_constraint,
            )

        return candidate_constraint

    def update_constraint(
        self,
        data_model_id: str,
        actor_user_id: str,
        request: UpdateConstraintRequest,
    ) -> dict[str, Any] | None:
        """Replace an existing deterministic field constraint."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        existing = request.existing.model_dump()
        updated = request.constraint.model_dump()

        constraints = specification.setdefault(
            "constraints",
            [],
        )

        existing_index = next(
            (
                index
                for index, constraint in enumerate(constraints)
                if constraint == existing
            ),
            None,
        )

        if existing_index is None:
            raise ValueError(
                "Existing constraint was not found."
            )

        entity = next(
            (
                item
                for item in specification.get("entities", [])
                if item.get("name") == updated["entity"]
            ),
            None,
        )

        if entity is None:
            raise ValueError(
                f"Unknown entity: {updated['entity']}"
            )

        field = next(
            (
                item
                for item in entity.get("fields", [])
                if item.get("name") == updated["field"]
            ),
            None,
        )

        if field is None:
            raise ValueError(
                f"Unknown field: "
                f"{updated['entity']}.{updated['field']}"
            )

        self._validate_constraint_compatibility(
            field=field,
            operator=updated["operator"],
        )

        for index, constraint in enumerate(constraints):
            if index != existing_index and constraint == updated:
                raise ValueError(
                    "Constraint already exists."
                )

        candidate = deepcopy(specification)
        candidate["constraints"][existing_index] = updated

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.CONSTRAINT_UPDATED,
                title="Constraint updated",
                description=(
                    f"Updated constraint on "
                    f"'{updated['entity']}.{updated['field']}'"
                ),
                data_model_id=data_model_id,
                metadata={
                    "previous": existing,
                    "updated": updated,
                },
            )

        return updated

    def delete_constraint(
        self,
        data_model_id: str,
        actor_user_id: str,
        request: dict[str, Any],
    ) -> bool:
        """Delete an existing deterministic field constraint."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return False

        constraints = specification.setdefault(
            "constraints",
            [],
        )

        index = next(
            (
                index
                for index, constraint in enumerate(constraints)
                if constraint == request
            ),
            None,
        )

        if index is None:
            return False

        candidate = deepcopy(specification)
        deleted = candidate["constraints"].pop(index)

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.CONSTRAINT_DELETED,
                title="Constraint deleted",
                description=(
                    f"Deleted constraint on "
                    f"'{deleted.get('entity')}.{deleted.get('field')}'"
                ),
                data_model_id=data_model_id,
                metadata=deleted,
            )

        return True

    def delete_entity(
        self,
        data_model_id: str,
        actor_user_id: str,
        entity_name: str,
    ) -> bool:
        """Delete an entity when no specification references depend on it."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return False

        entities = specification.setdefault("entities", [])

        entity = next(
            (
                item
                for item in entities
                if item.get("name") == entity_name
            ),
            None,
        )

        if entity is None:
            return False

        relationships = specification.get(
            "relationships",
            [],
        )

        for relationship in relationships:
            for key in ("source", "target"):
                reference = relationship.get(key)

                if (
                    isinstance(reference, str)
                    and reference.split(".", 1)[0] == entity_name
                ):
                    raise ValueError(
                        f"Entity '{entity_name}' is referenced by "
                        "a relationship."
                    )

        foreign_keys = specification.get(
            "foreign_keys",
            [],
        )

        for foreign_key in foreign_keys:
            for key in ("source", "target"):
                endpoint = foreign_key.get(key, {})

                if (
                    isinstance(endpoint, dict)
                    and endpoint.get("entity") == entity_name
                ):
                    raise ValueError(
                        f"Entity '{entity_name}' is referenced by "
                        "a foreign key."
                    )

        dependencies = specification.get(
            "dependencies",
            [],
        )

        for dependency in dependencies:
            references = [
                dependency.get("target"),
                *dependency.get("source_fields", []),
            ]

            if any(
                isinstance(reference, str)
                and reference.split(".", 1)[0] == entity_name
                for reference in references
            ):
                raise ValueError(
                    f"Entity '{entity_name}' is referenced by "
                    "a dependency."
                )

        candidate = deepcopy(specification)

        candidate["entities"] = [
            item
            for item in candidate["entities"]
            if item.get("name") != entity_name
        ]

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.ENTITY_DELETED,
                title="Entity deleted",
                description=f"Deleted entity '{entity_name}'",
                data_model_id=data_model_id,
                metadata={
                    "entity_name": entity_name,
                },
            )

        return True
