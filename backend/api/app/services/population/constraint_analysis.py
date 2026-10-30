"""Derive structural population constraints from a FORGE specification.

This module analyses specifications. It does not allocate populations or
claim that stochastic relationship generation guarantees cardinality.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.relationship_endpoint import parse_relationship_endpoint


@dataclass(frozen=True)
class PopulationDefinition:
    entity: str
    count: int | None
    scaling: str


@dataclass(frozen=True)
class ForeignKeyDependency:
    name: str
    child_entity: str
    child_fields: tuple[str, ...]
    parent_entity: str
    parent_fields: tuple[str, ...]


@dataclass(frozen=True)
class IdentityComponent:
    kind: str
    fields: tuple[str, ...]
    parent_entity: str | None = None
    parent_fields: tuple[str, ...] = ()
    capacity: int | None = None


@dataclass(frozen=True)
class IdentityCapacity:
    entity: str
    components: tuple[IdentityComponent, ...]
    finite_multiplier: int
    parent_entities: tuple[str, ...]
    unbounded: bool
    supported: bool


@dataclass(frozen=True)
class PopulationConstraint:
    """A necessary population-level constraint."""

    kind: str
    entity: str
    related_entities: tuple[str, ...] = ()
    multiplier: int = 1
    relationship: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class RelationshipAnalysis:
    source: str
    target: str
    relationship_type: str
    source_participation: str
    target_participation: str
    status: str
    fk_name: str | None = None
    fk_direction: str | None = None
    child_entity: str | None = None
    parent_entity: str | None = None
    requires_generation_validation: bool = True
    reason: str | None = None


@dataclass
class ConstraintAnalysis:
    populations: list[PopulationDefinition] = field(default_factory=list)
    foreign_key_dependencies: list[ForeignKeyDependency] = field(default_factory=list)
    identity_capacities: list[IdentityCapacity] = field(default_factory=list)
    relationships: list[RelationshipAnalysis] = field(default_factory=list)
    population_constraints: list[PopulationConstraint] = field(
        default_factory=list
    )
    diagnostics: list[dict[str, str]] = field(default_factory=list)

    @property
    def structurally_valid(self) -> bool:
        return not any(
            item["severity"] == "ERROR"
            for item in self.diagnostics
        )

    @property
    def allocation_supported(self) -> bool:
        if not self.structurally_valid:
            return False

        return (
            all(capacity.supported for capacity in self.identity_capacities)
            and all(
                relationship.status == "MAPPED"
                for relationship in self.relationships
            )
        )

    @property
    def generation_guaranteed(self) -> bool:
        if not self.structurally_valid:
            return False

        return all(
            relationship.status == "MAPPED"
            and not relationship.requires_generation_validation
            for relationship in self.relationships
        )

    @property
    def supported(self) -> bool:
        """Backward-compatible alias for structural validity."""
        return self.structurally_valid

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["structurally_valid"] = self.structurally_valid
        result["allocation_supported"] = self.allocation_supported
        result["generation_guaranteed"] = self.generation_guaranteed
        result["supported"] = self.supported
        return result


def _diagnostic(
    result: ConstraintAnalysis,
    code: str,
    severity: str,
    message: str,
    subject: str,
) -> None:
    result.diagnostics.append({
        "code": code,
        "severity": severity,
        "message": message,
        "subject": subject,
    })


def _local_identity_capacity(field_spec: dict[str, Any]) -> int | None:
    """Return finite local identity capacity, or None for sequential IDs."""
    identity = field_spec.get("identity") or {}
    generation = field_spec.get("generation") or {}

    if (
        field_spec.get("type") == "IDENTIFIER"
        and identity.get("strategy") == "SEQUENTIAL_ID"
    ):
        return None

    strategy = generation.get("strategy")
    distribution = generation.get("distribution")
    parameters = generation.get("parameters") or {}

    if strategy == "RANDOM" and distribution == "CATEGORICAL":
        values = parameters.get("values")
        if not isinstance(values, list) or not values:
            raise ValueError(
                "CATEGORICAL identity requires a non-empty values list."
            )
        try:
            return len(dict.fromkeys(values))
        except TypeError:
            raise ValueError(
                "CATEGORICAL identity values must be hashable."
            ) from None

    if (
        field_spec.get("type") == "INTEGER"
        and strategy == "RANDOM"
        and distribution in {"UNIFORM", "DISCRETE_UNIFORM"}
    ):
        minimum = parameters.get("minimum")
        maximum = parameters.get("maximum")

        if (
            minimum is None or maximum is None
            or isinstance(minimum, bool) or isinstance(maximum, bool)
        ):
            raise ValueError(
                "INTEGER identity requires numeric minimum and maximum bounds."
            )

        try:
            low = Decimal(str(minimum))
            high = Decimal(str(maximum))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("INTEGER identity has invalid numeric bounds.") from None

        if not low.is_finite() or not high.is_finite():
            raise ValueError("INTEGER identity bounds must be finite.")
        if low != low.to_integral_value() or high != high.to_integral_value():
            raise ValueError("INTEGER identity bounds must be whole numbers.")
        if low > high:
            raise ValueError("INTEGER identity minimum exceeds maximum.")

        return int(high - low + 1)

    raise ValueError(
        "Unsupported locally generated identity configuration for field "
        f"{field_spec.get('name', '<unknown>')}."
    )


def analyze_specification_constraints(
    specification: dict[str, Any],
) -> ConstraintAnalysis:
    """Analyse populations, foreign keys, identity capacity and relationships.

    A positive child population requires a non-empty parent keyspace for each
    FK. Identity capacities are expressed as products of parent keyspaces and
    finite local identity domains. Relationship cardinality and participation
    remain generation-time checks because FK assignment uses replacement.
    """
    result = ConstraintAnalysis()

    if not isinstance(specification, dict):
        _diagnostic(
            result, "INVALID_SPECIFICATION", "ERROR",
            "Specification must be an object.", "specification",
        )
        return result

    entities = specification.get("entities")
    if not isinstance(entities, list):
        _diagnostic(
            result, "INVALID_ENTITIES", "ERROR",
            "Specification entities must be a list.", "entities",
        )
        return result

    if not entities:
        _diagnostic(
            result, "EMPTY_ENTITIES", "ERROR",
            "Specification must contain at least one entity.",
            "entities",
        )
        return result

    entity_map: dict[str, dict[str, Any]] = {}

    for entity in entities:
        if not isinstance(entity, dict) or not isinstance(entity.get("name"), str):
            _diagnostic(
                result, "INVALID_ENTITY", "ERROR",
                "Every entity must be an object with a name.", "entities",
            )
            continue

        name = entity["name"]
        if name in entity_map:
            _diagnostic(
                result, "DUPLICATE_ENTITY", "ERROR",
                f"Entity {name!r} is declared more than once.", name,
            )
            continue

        entity_map[name] = entity
        population = entity.get("population") or {}
        scaling = str(population.get("scaling", "SCALABLE")).upper()
        count = population.get("count")

        if count is not None and (
            isinstance(count, bool) or not isinstance(count, int) or count < 0
        ):
            _diagnostic(
                result, "INVALID_POPULATION_COUNT", "ERROR",
                "Population count must be a non-negative integer or null.", name,
            )

        if scaling not in {"FIXED", "SCALABLE"}:
            _diagnostic(
                result, "UNSUPPORTED_SCALING", "ERROR",
                f"Unsupported persisted population scaling mode: {scaling}.", name,
            )

        if scaling == "FIXED" and count is None:
            _diagnostic(
                result, "FIXED_COUNT_MISSING", "ERROR",
                "FIXED population requires an explicit count.", name,
            )

        result.populations.append(PopulationDefinition(name, count, scaling))

    fields_by_entity = {
        name: {
            field["name"]
            for field in entity.get("fields", [])
            if isinstance(field, dict)
            and isinstance(field.get("name"), str)
        }
        for name, entity in entity_map.items()
    }

    foreign_keys = specification.get("foreign_keys", [])
    if not isinstance(foreign_keys, list):
        _diagnostic(
            result, "INVALID_FOREIGN_KEYS", "ERROR",
            "Foreign keys must be a list.", "foreign_keys",
        )
        foreign_keys = []

    fk_records: list[dict[str, Any]] = []

    for index, fk in enumerate(foreign_keys, start=1):
        subject = (
            str(fk.get("name", f"foreign_key_{index}"))
            if isinstance(fk, dict) else f"foreign_key_{index}"
        )

        if not isinstance(fk, dict):
            _diagnostic(
                result, "INVALID_FOREIGN_KEY", "ERROR",
                "Foreign key must be an object.", subject,
            )
            continue

        source = fk.get("source")
        target = fk.get("target")

        if not isinstance(source, dict) or not isinstance(target, dict):
            _diagnostic(
                result, "INVALID_FOREIGN_KEY_ENDPOINT", "ERROR",
                "Foreign key source and target must be objects.", subject,
            )
            continue

        child = source.get("entity")
        parent = target.get("entity")
        child_fields = source.get("fields")
        parent_fields = target.get("fields")

        valid_fields = (
            isinstance(child_fields, list)
            and isinstance(parent_fields, list)
            and bool(child_fields)
            and len(child_fields) == len(parent_fields)
            and all(isinstance(item, str) for item in child_fields + parent_fields)
        )

        if child not in entity_map or parent not in entity_map or not valid_fields:
            _diagnostic(
                result, "INVALID_FOREIGN_KEY_MAPPING", "ERROR",
                "Foreign key has unknown entities or invalid/mismatched field lists.",
                subject,
            )
            continue

        if child == parent:
            _diagnostic(
                result, "SELF_REFERENCING_FOREIGN_KEY", "ERROR",
                "Foreign keys must reference a different source and target entity.",
                subject,
            )
            continue

        if (
            len(set(child_fields)) != len(child_fields)
            or len(set(parent_fields)) != len(parent_fields)
        ):
            _diagnostic(
                result, "DUPLICATE_FOREIGN_KEY_FIELD", "ERROR",
                "Foreign key source and target fields must not contain duplicates.",
                subject,
            )
            continue

        missing_child_fields = (
            set(child_fields) - fields_by_entity[child]
        )
        missing_parent_fields = (
            set(parent_fields) - fields_by_entity[parent]
        )

        if missing_child_fields or missing_parent_fields:
            missing = sorted(
                f"{entity_name}.{field_name}"
                for entity_name, names in (
                    (child, missing_child_fields),
                    (parent, missing_parent_fields),
                )
                for field_name in names
            )
            _diagnostic(
                result, "FOREIGN_KEY_FIELD_MISSING", "ERROR",
                "Foreign key references unknown fields: "
                + ", ".join(missing) + ".",
                subject,
            )
            continue

        parent_identity = (
            entity_map[parent].get("identity") or {}
        ).get("fields", [])

        if not parent_identity:
            _diagnostic(
                result, "FOREIGN_KEY_PARENT_IDENTITY_MISSING", "ERROR",
                "Foreign key target entity must define an identity.",
                subject,
            )
            continue

        if parent_fields != parent_identity:
            _diagnostic(
                result, "FOREIGN_KEY_TARGET_IDENTITY_MISMATCH", "ERROR",
                "Foreign key target fields must exactly match the parent "
                "identity fields in the same order.",
                subject,
            )
            continue

        record = {
            "name": subject,
            "child": child,
            "child_fields": tuple(child_fields),
            "parent": parent,
            "parent_fields": tuple(parent_fields),
        }
        fk_records.append(record)

        result.foreign_key_dependencies.append(
            ForeignKeyDependency(
                subject, child, tuple(child_fields),
                parent, tuple(parent_fields),
            )
        )

    # Identity capacity follows EntityGenerator's FK-first Cartesian model.
    for entity_name, entity in entity_map.items():
        identity = entity.get("identity") or {}
        identity_fields = identity.get("fields") or []

        if not identity_fields:
            result.identity_capacities.append(
                IdentityCapacity(entity_name, (), 1, (), True, True)
            )
            continue

        if (
            not isinstance(identity_fields, list)
            or any(not isinstance(item, str) for item in identity_fields)
            or len(set(identity_fields)) != len(identity_fields)
        ):
            _diagnostic(
                result, "INVALID_IDENTITY_FIELDS", "ERROR",
                "Identity fields must be a unique list of field names.", entity_name,
            )
            result.identity_capacities.append(
                IdentityCapacity(entity_name, (), 1, (), False, False)
            )
            continue

        fields = entity.get("fields") or []
        fields_by_name = {
            item["name"]: item
            for item in fields
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }

        identity_set = set(identity_fields)
        components: list[IdentityComponent] = []
        covered: set[str] = set()
        parent_entities: list[str] = []
        finite_multiplier = 1
        unbounded = False
        supported = True

        entity_fks = [
            fk for fk in fk_records if fk["child"] == entity_name
        ]

        for fk in entity_fks:
            child_fields = set(fk["child_fields"])
            overlap = child_fields & identity_set

            if (
                len(fk["child_fields"]) > 1
                and overlap
                and not child_fields.issubset(identity_set)
            ):
                supported = False
                _diagnostic(
                    result, "PARTIAL_COMPOSITE_IDENTITY_FK", "ERROR",
                    "A composite FK partially overlaps the child identity. "
                    "The generation identity allocator cannot safely model it.",
                    fk["name"],
                )
                continue

            if not child_fields.issubset(identity_set):
                continue

            if covered & child_fields:
                supported = False
                _diagnostic(
                    result, "OVERLAPPING_IDENTITY_COMPONENTS", "ERROR",
                    "Multiple foreign keys cover the same identity fields.",
                    fk["name"],
                )
                continue

            components.append(IdentityComponent(
                "FOREIGN_KEY",
                fk["child_fields"],
                fk["parent"],
                fk["parent_fields"],
                None,
            ))
            covered.update(child_fields)

            if fk["parent"] not in parent_entities:
                parent_entities.append(fk["parent"])

        for field_name in identity_fields:
            if field_name in covered:
                continue

            field_spec = fields_by_name.get(field_name)
            if field_spec is None:
                supported = False
                _diagnostic(
                    result, "IDENTITY_FIELD_MISSING", "ERROR",
                    f"Identity field {field_name!r} is missing from entity fields.",
                    entity_name,
                )
                continue

            try:
                capacity = _local_identity_capacity(field_spec)
            except ValueError as exc:
                supported = False
                _diagnostic(
                    result, "UNSUPPORTED_LOCAL_IDENTITY", "ERROR",
                    str(exc), f"{entity_name}.{field_name}",
                )
                continue

            components.append(
                IdentityComponent("LOCAL", (field_name,), capacity=capacity)
            )
            covered.add(field_name)

            if capacity is None:
                unbounded = True
            else:
                finite_multiplier *= capacity

        if covered != identity_set:
            supported = False
            _diagnostic(
                result, "IDENTITY_COVERAGE_INCOMPLETE", "ERROR",
                "Generation identity components do not cover every declared identity field.",
                entity_name,
            )

        result.identity_capacities.append(IdentityCapacity(
            entity_name,
            tuple(components),
            finite_multiplier,
            tuple(parent_entities),
            unbounded,
            supported,
        ))

    # Match relationship declarations exactly as GenerationValidator does.
    relationships = specification.get("relationships", [])
    if not isinstance(relationships, list):
        _diagnostic(
            result, "INVALID_RELATIONSHIPS", "ERROR",
            "Relationships must be a list.", "relationships",
        )
        relationships = []

    for index, relationship in enumerate(relationships, start=1):
        if not isinstance(relationship, dict):
            _diagnostic(
                result, "INVALID_RELATIONSHIP", "ERROR",
                "Relationship must be an object.", f"relationship_{index}",
            )
            continue

        source_raw = relationship.get("source")
        target_raw = relationship.get("target")
        rel_type = str(relationship.get("type", "UNKNOWN")).upper()
        source_participation = str(
            relationship.get("source_participation", "MANDATORY")
        ).upper()
        target_participation = str(
            relationship.get("target_participation", "MANDATORY")
        ).upper()

        source_label = str(source_raw)
        target_label = str(target_raw)
        subject = f"{source_label}->{target_label}"

        def add_relationship(
            status: str,
            reason: str,
            fk: dict[str, Any] | None = None,
            direction: str | None = None,
            child: str | None = None,
            parent: str | None = None,
        ) -> None:
            result.relationships.append(RelationshipAnalysis(
                source=source_label,
                target=target_label,
                relationship_type=rel_type,
                source_participation=source_participation,
                target_participation=target_participation,
                status=status,
                fk_name=fk["name"] if fk else None,
                fk_direction=direction,
                child_entity=child,
                parent_entity=parent,
                reason=reason,
            ))

        if rel_type == "MANY_TO_MANY":
            reason = (
                "Direct MANY_TO_MANY declarations do not identify an "
                "association mapping."
            )
            add_relationship("UNSUPPORTED", reason)
            _diagnostic(
                result, "UNSUPPORTED_MANY_TO_MANY", "WARNING",
                "Explicit junction or association evidence is required.", subject,
            )
            continue

        if rel_type not in {"ONE_TO_ONE", "ONE_TO_MANY", "MANY_TO_ONE"}:
            reason = f"Unsupported relationship type: {rel_type}."
            add_relationship("UNSUPPORTED", reason)
            _diagnostic(
                result, "UNSUPPORTED_RELATIONSHIP_TYPE", "WARNING",
                reason, subject,
            )
            continue

        if (
            source_participation not in {"MANDATORY", "OPTIONAL"}
            or target_participation not in {"MANDATORY", "OPTIONAL"}
        ):
            reason = "Participation must be MANDATORY or OPTIONAL."
            add_relationship("INVALID", reason)
            _diagnostic(
                result, "INVALID_RELATIONSHIP_PARTICIPATION", "ERROR",
                reason, subject,
            )
            continue

        try:
            source_endpoint = parse_relationship_endpoint(
                source_raw, "source"
            )
            target_endpoint = parse_relationship_endpoint(
                target_raw, "target"
            )
        except ValueError as exc:
            reason = str(exc)
            add_relationship("INVALID", reason)
            _diagnostic(
                result, "INVALID_RELATIONSHIP_ENDPOINT", "ERROR",
                reason, subject,
            )
            continue

        source_label = source_endpoint.reference
        target_label = target_endpoint.reference
        subject = f"{source_label}->{target_label}"

        source_entity = source_endpoint.entity
        target_entity = target_endpoint.entity
        source_fields = source_endpoint.fields
        target_fields = target_endpoint.fields

        if source_entity not in entity_map or target_entity not in entity_map:
            reason = "Relationship references an unknown entity."
            add_relationship("INVALID", reason)
            _diagnostic(
                result, "UNKNOWN_RELATIONSHIP_ENTITY", "ERROR",
                reason, subject,
            )
            continue

        missing_source_fields = (
            set(source_fields) - fields_by_entity[source_entity]
        )
        missing_target_fields = (
            set(target_fields) - fields_by_entity[target_entity]
        )

        if missing_source_fields or missing_target_fields:
            missing = []
            if missing_source_fields:
                missing.append(
                    f"{source_entity}: {sorted(missing_source_fields)}"
                )
            if missing_target_fields:
                missing.append(
                    f"{target_entity}: {sorted(missing_target_fields)}"
                )

            reason = (
                "Relationship references unknown fields: "
                + "; ".join(missing)
            )
            add_relationship("INVALID", reason)
            _diagnostic(
                result, "UNKNOWN_RELATIONSHIP_FIELD", "ERROR",
                reason, subject,
            )
            continue

        matching: list[tuple[dict[str, Any], str]] = []
        partial_composite = False

        for fk in fk_records:
            forward = (
                fk["child"] == source_entity
                and fk["child_fields"] == source_fields
                and fk["parent"] == target_entity
                and fk["parent_fields"] == target_fields
            )
            reverse = (
                fk["child"] == target_entity
                and fk["child_fields"] == target_fields
                and fk["parent"] == source_entity
                and fk["parent_fields"] == source_fields
            )

            if forward:
                matching.append((fk, "FORWARD"))
            elif reverse:
                matching.append((fk, "REVERSE"))
            elif (
                fk["child"] == source_entity
                and fk["parent"] == target_entity
                and bool(set(source_fields) & set(fk["child_fields"]))
                and bool(set(target_fields) & set(fk["parent_fields"]))
            ) or (
                fk["child"] == target_entity
                and fk["parent"] == source_entity
                and bool(set(target_fields) & set(fk["child_fields"]))
                and bool(set(source_fields) & set(fk["parent_fields"]))
            ):
                partial_composite = True

        expected = {
            "ONE_TO_ONE": None,
            "ONE_TO_MANY": "REVERSE",
            "MANY_TO_ONE": "FORWARD",
        }[rel_type]

        compatible = [
            (fk, direction)
            for fk, direction in matching
            if expected is None or direction == expected
        ]

        if len(compatible) != 1:
            if len(compatible) > 1:
                reason = (
                    "Multiple compatible foreign keys match this relationship."
                )
                code = "AMBIGUOUS_RELATIONSHIP_MAPPING"
            elif partial_composite:
                reason = (
                    "Relationship endpoints match only part of a composite "
                    "foreign key; the validator does not treat that as a "
                    "relationship mapping."
                )
                code = "PARTIAL_COMPOSITE_RELATIONSHIP_MAPPING"
            elif matching:
                reason = (
                    "Matching foreign keys exist, but their direction conflicts "
                    "with the declared cardinality."
                )
                code = "RELATIONSHIP_DIRECTION_MISMATCH"
            else:
                reason = (
                    "A complete ordered foreign key mapping in the expected "
                    "direction could not be established."
                )
                code = "RELATIONSHIP_FK_NOT_FOUND"

            add_relationship("UNMAPPED", reason)
            _diagnostic(result, code, "WARNING", reason, subject)
            continue

        fk, direction = compatible[0]
        child = source_entity if direction == "FORWARD" else target_entity
        parent = target_entity if direction == "FORWARD" else source_entity

        add_relationship(
            "MAPPED",
            "Complete ordered FK mapping matches the generation validator. "
            "Row-level cardinality and participation still require "
            "generation-time verification.",
            fk,
            direction,
            child,
            parent,
        )

    # Every positive child population requires a non-empty keyspace
    # for each referenced parent.
    for dependency in result.foreign_key_dependencies:
        result.population_constraints.append(PopulationConstraint(
            kind="PARENT_REQUIRED_FOR_POSITIVE_CHILD",
            entity=dependency.child_entity,
            related_entities=(dependency.parent_entity,),
            relationship=dependency.name,
            reason=(
                f"A positive {dependency.child_entity} population requires "
                f"at least one {dependency.parent_entity} identity key."
            ),
        ))

    # Derive finite identity limits. An unbounded local identity component
    # removes the finite upper bound, but FK parent requirements still apply.
    for capacity in result.identity_capacities:
        if not capacity.supported or capacity.unbounded:
            continue

        result.population_constraints.append(PopulationConstraint(
            kind="IDENTITY_CAPACITY",
            entity=capacity.entity,
            related_entities=capacity.parent_entities,
            multiplier=capacity.finite_multiplier,
            reason=(
                f"{capacity.entity} identity capacity is limited by "
                f"its finite local multiplier ({capacity.finite_multiplier}) "
                "and parent keyspaces."
            ),
        ))

    # Derive necessary relationship inequalities using the resolved
    # child/parent direction from GenerationValidator-compatible mapping.
    for relationship in result.relationships:
        if relationship.status != "MAPPED":
            continue

        parent_participation = (
            relationship.target_participation
            if relationship.fk_direction == "FORWARD"
            else relationship.source_participation
        )

        if parent_participation == "MANDATORY":
            result.population_constraints.append(PopulationConstraint(
                kind="CHILD_AT_LEAST_PARENT",
                entity=relationship.child_entity,
                related_entities=(relationship.parent_entity,),
                relationship=(
                    f"{relationship.source} -> {relationship.target}"
                ),
                reason=(
                    "Mandatory parent participation requires every parent "
                    "record to have at least one child record."
                ),
            ))

        if relationship.relationship_type == "ONE_TO_ONE":
            result.population_constraints.append(PopulationConstraint(
                kind="CHILD_AT_MOST_PARENT",
                entity=relationship.child_entity,
                related_entities=(relationship.parent_entity,),
                relationship=(
                    f"{relationship.source} -> {relationship.target}"
                ),
                reason=(
                    "ONE_TO_ONE cardinality requires unique child references "
                    "to parent identity values."
                ),
            ))

    return result
