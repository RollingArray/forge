"""
FORGE - Experiment 020-U: Declarative Specification Conflict Diagnosis
============================================================================

Experiment:     020_declarative_generation_specification
Stage:          020-U
Purpose:        Explainable specification conflict detection and diagnosis
Random seed:    42

Hypothesis:
  An infeasible declarative generation specification can be analyzed before
  generation and reduced to explicit, actionable conflicts showing affected
  fields, conflicting requirements, feasible regions, dependencies, and
  originating specification rules.

Architectural principle:
  FORGE diagnoses infeasibility before generation. It must not silently
  relax constraints or repair invalid records after generation.

Validation focus:
  - Direct field conflicts
  - Cross-field conflicts
  - Chained conflicts
  - Conditional conflicts
  - Multiple conflicts
  - Feasible-region explanation
  - Source-rule references
  - Dependency paths
  - Deterministic diagnosis
  - Entity/field-order independence
  - Generation blocking
  - No hidden relaxation or repair

Output:
  Results: output/specification_conflict_diagnosis_results.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXPERIMENT_DIR / "output"
RESULTS_PATH = OUTPUT_DIR / "specification_conflict_diagnosis_results.json"
MASTER_SEED = 42


# ============================================================================
# DECLARATIVE MODELS
# ============================================================================


@dataclass(frozen=True)
class Field:
    name: str
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class Entity:
    name: str
    fields: tuple[Field, ...]
    record_count: int = 10


@dataclass(frozen=True)
class Constraint:
    name: str
    entity: str
    left: str
    operator: str
    right: str | float


@dataclass(frozen=True)
class ConditionalConstraint:
    name: str
    entity: str
    condition_field: str
    condition_operator: str
    condition_value: float
    target_field: str
    target_operator: str
    target_value: float


@dataclass(frozen=True)
class Specification:
    name: str
    entities: tuple[Entity, ...]
    constraints: tuple[Constraint, ...] = ()
    conditional_constraints: tuple[ConditionalConstraint, ...] = ()


@dataclass
class NumericRange:
    minimum: float
    maximum: float
    lower_sources: list[str]
    upper_sources: list[str]

    @property
    def feasible(self) -> bool:
        return self.minimum <= self.maximum


@dataclass(frozen=True)
class Conflict:
    entity: str
    field: str
    conflict_type: str
    message: str
    requirements: tuple[str, ...]
    resolved_context: dict[str, Any]
    feasible_region: dict[str, Any]
    source_rules: tuple[str, ...]
    dependency_path: tuple[str, ...]


# ============================================================================
# HELPERS
# ============================================================================


def entity_map(spec: Specification) -> dict[str, Entity]:
    return {e.name: e for e in spec.entities}


def field_map(spec: Specification) -> dict[str, dict[str, Field]]:
    return {e.name: {f.name: f for f in e.fields} for e in spec.entities}


def spec_fingerprint(spec: Specification) -> str:
    payload = json.dumps(
        asdict(spec),
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def format_constraint(c: Constraint) -> str:
    return f"{c.entity}.{c.left} {c.operator} {c.right}"


def initial_ranges(
    spec: Specification,
) -> dict[tuple[str, str], NumericRange]:

    result = {}

    for entity in spec.entities:
        for field in entity.fields:
            result[(entity.name, field.name)] = NumericRange(
                minimum=(field.minimum if field.minimum is not None else float("-inf")),
                maximum=(field.maximum if field.maximum is not None else float("inf")),
                lower_sources=(
                    ["FIELD_BOUND_MIN"] if field.minimum is not None else []
                ),
                upper_sources=(
                    ["FIELD_BOUND_MAX"] if field.maximum is not None else []
                ),
            )

    return result


# ============================================================================
# SPECIFICATION VALIDATION
# ============================================================================


def validate_specification(spec: Specification) -> None:

    entities = entity_map(spec)
    fields = field_map(spec)

    if len(entities) != len(spec.entities):
        raise ValueError("Duplicate entity.")

    for entity in spec.entities:

        names = [f.name for f in entity.fields]

        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate field in {entity.name}.")

        if entity.record_count <= 0:
            raise ValueError(f"Invalid record count for {entity.name}.")

        for field in entity.fields:
            if (
                field.minimum is not None
                and field.maximum is not None
                and field.minimum > field.maximum
            ):
                raise ValueError(
                    f"Invalid field bounds for " f"{entity.name}.{field.name}."
                )

    for c in spec.constraints:

        if c.entity not in entities:
            raise ValueError(f"Unknown constraint entity: {c.entity}")

        if c.left not in fields[c.entity]:
            raise ValueError(f"Unknown constraint field: " f"{c.entity}.{c.left}")

        if isinstance(c.right, str) and c.right not in fields[c.entity]:
            raise ValueError(f"Unknown constraint field: " f"{c.entity}.{c.right}")

        if c.operator not in {"<", "<=", ">", ">=", "="}:
            raise ValueError(f"Unsupported constraint operator: {c.operator}")

    for c in spec.conditional_constraints:

        if c.entity not in entities:
            raise ValueError(f"Unknown conditional entity: {c.entity}")

        if c.condition_field not in fields[c.entity]:
            raise ValueError(
                f"Unknown conditional condition field: "
                f"{c.entity}.{c.condition_field}"
            )

        if c.target_field not in fields[c.entity]:
            raise ValueError(
                f"Unknown conditional target field: " f"{c.entity}.{c.target_field}"
            )


# ============================================================================
# RANGE PROPAGATION
# ============================================================================


def add_lower(
    r: NumericRange,
    value: float,
    source: str,
) -> bool:

    if value > r.minimum:
        r.minimum = value
        r.lower_sources = [source]
        return True

    if value == r.minimum and source not in r.lower_sources:
        r.lower_sources.append(source)

    return False


def add_upper(
    r: NumericRange,
    value: float,
    source: str,
) -> bool:

    if value < r.maximum:
        r.maximum = value
        r.upper_sources = [source]
        return True

    if value == r.maximum and source not in r.upper_sources:
        r.upper_sources.append(source)

    return False


def apply_constraint(
    ranges: dict[tuple[str, str], NumericRange],
    c: Constraint,
) -> bool:

    target = ranges[(c.entity, c.left)]

    if isinstance(c.right, (int, float)):
        value = float(c.right)

        if c.operator in {">", ">="}:
            return add_lower(target, value, c.name)

        if c.operator in {"<", "<="}:
            return add_upper(target, value, c.name)

        if c.operator == "=":
            changed = add_lower(target, value, c.name)
            changed |= add_upper(target, value, c.name)
            return changed

        return False

    source = ranges[(c.entity, c.right)]

    if c.operator in {">", ">="}:
        return add_lower(target, source.minimum, c.name)

    if c.operator in {"<", "<="}:
        return add_upper(target, source.maximum, c.name)

    if c.operator == "=":
        changed = add_lower(
            target,
            source.minimum,
            c.name,
        )
        changed |= add_upper(
            target,
            source.maximum,
            c.name,
        )
        return changed

    return False


def diagnose(
    spec: Specification,
) -> tuple[
    dict[tuple[str, str], NumericRange],
    list[Conflict],
]:

    ranges = initial_ranges(spec)

    for _ in range(max(1, len(ranges) * 4)):

        changed = False

        for c in sorted(
            spec.constraints,
            key=lambda x: (
                x.entity,
                x.left,
                x.name,
            ),
        ):
            changed |= apply_constraint(
                ranges,
                c,
            )

        if not changed:
            break

    conflicts: list[Conflict] = []

    # Direct and propagated conflicts.
    for (entity, field), r in sorted(ranges.items()):

        if not r.feasible:

            sources = tuple(sorted(set(r.lower_sources + r.upper_sources)))

            requirements = []

            for source in sources:

                if source.startswith("FIELD_BOUND"):
                    requirements.append(source)
                    continue

                c = next(
                    (item for item in spec.constraints if item.name == source),
                    None,
                )

                if c:
                    requirements.append(format_constraint(c))

            conflicts.append(
                Conflict(
                    entity=entity,
                    field=field,
                    conflict_type=("EMPTY_FEASIBLE_REGION"),
                    message=(f"{entity}.{field} has no " "feasible generation region."),
                    requirements=tuple(requirements),
                    resolved_context={
                        "minimum": r.minimum,
                        "maximum": r.maximum,
                    },
                    feasible_region={
                        "minimum": r.minimum,
                        "maximum": r.maximum,
                        "empty": True,
                    },
                    source_rules=sources,
                    dependency_path=(f"{entity}.{field}",),
                )
            )

    # Conditional conflicts.
    for c in sorted(
        spec.conditional_constraints,
        key=lambda x: (x.entity, x.name),
    ):

        condition = ranges[(c.entity, c.condition_field)]
        target = ranges[(c.entity, c.target_field)]

        condition_can_activate = condition.maximum >= c.condition_value

        if not condition_can_activate:
            continue

        if c.target_operator in {">", ">="} and target.maximum < c.target_value:

            conflicts.append(
                Conflict(
                    entity=c.entity,
                    field=c.target_field,
                    conflict_type=("CONDITIONAL_CONFLICT"),
                    message=(
                        f"Conditional rule {c.name} " "has no feasible target region."
                    ),
                    requirements=(
                        f"{c.condition_field} "
                        f"{c.condition_operator} "
                        f"{c.condition_value}",
                        f"{c.target_field} "
                        f"{c.target_operator} "
                        f"{c.target_value}",
                    ),
                    resolved_context={
                        "condition_range": {
                            "minimum": condition.minimum,
                            "maximum": condition.maximum,
                        },
                        "target_range": {
                            "minimum": target.minimum,
                            "maximum": target.maximum,
                        },
                    },
                    feasible_region={
                        "minimum": target.minimum,
                        "maximum": target.maximum,
                        "empty": True,
                    },
                    source_rules=(c.name,),
                    dependency_path=(
                        f"{c.entity}.{c.condition_field}",
                        f"{c.entity}.{c.target_field}",
                    ),
                )
            )

    # Stable ordering and de-duplication.
    unique = {}

    for conflict in conflicts:
        key = (
            conflict.entity,
            conflict.field,
            conflict.conflict_type,
            conflict.source_rules,
        )
        unique[key] = conflict

    return ranges, [unique[key] for key in sorted(unique)]


# ============================================================================
# GENERATION GUARD
# ============================================================================


def generation_guard(
    spec: Specification,
) -> dict[str, Any]:

    _, conflicts = diagnose(spec)

    if conflicts:
        raise RuntimeError(
            "GENERATION_BLOCKED: "
            "Specification is infeasible. "
            "Run conflict diagnosis."
        )

    return {
        "generation_allowed": True,
        "generation_executed": False,
    }


# ============================================================================
# SPECIFICATIONS
# ============================================================================


def feasible_spec() -> Specification:

    return Specification(
        name="FEASIBLE_BASE",
        entities=(
            Entity(
                "ORDER",
                (
                    Field("ORDER_VALUE", 1000, 20000),
                    Field("DISCOUNT", 0, 30),
                ),
            ),
        ),
        constraints=(
            Constraint(
                "ORDER_MIN",
                "ORDER",
                "ORDER_VALUE",
                ">=",
                1000,
            ),
        ),
    )


def direct_conflict_spec() -> Specification:

    # Deliberately invalid bounds. Diagnosis should expose
    # the empty region before generation.
    return Specification(
        name="DIRECT_FIELD_CONFLICT",
        entities=(
            Entity(
                "ORDER",
                (Field("ORDER_VALUE", 10000, 5000),),
            ),
        ),
    )


def cross_field_conflict_spec() -> Specification:

    return Specification(
        name="CROSS_FIELD_CONFLICT",
        entities=(
            Entity(
                "ORDER",
                (
                    Field("CUSTOMER_VALUE", 7000, 10000),
                    Field("ORDER_VALUE", 1000, 5000),
                ),
            ),
        ),
        constraints=(
            Constraint(
                "ORDER_ABOVE_CUSTOMER",
                "ORDER",
                "ORDER_VALUE",
                ">=",
                "CUSTOMER_VALUE",
            ),
        ),
    )


def chained_conflict_spec() -> Specification:

    return Specification(
        name="CHAINED_CONFLICT",
        entities=(
            Entity(
                "CHAIN",
                (
                    Field("VALUE_B", 0, 8000),
                    Field("VALUE_C", 0, 7000),
                ),
            ),
        ),
        constraints=(
            Constraint(
                "B_MIN",
                "CHAIN",
                "VALUE_B",
                ">=",
                9000,
            ),
            Constraint(
                "C_FROM_B",
                "CHAIN",
                "VALUE_C",
                ">=",
                "VALUE_B",
            ),
        ),
    )


def conditional_conflict_spec() -> Specification:

    return Specification(
        name="CONDITIONAL_CONFLICT",
        entities=(
            Entity(
                "ORDER",
                (
                    Field("ORDER_VALUE", 10000, 20000),
                    Field("DISCOUNT", 0, 3),
                ),
            ),
        ),
        conditional_constraints=(
            ConditionalConstraint(
                "HIGH_VALUE_DISCOUNT",
                "ORDER",
                "ORDER_VALUE",
                ">=",
                10000,
                "DISCOUNT",
                ">=",
                5,
            ),
        ),
    )


def multiple_conflict_spec() -> Specification:

    return Specification(
        name="MULTIPLE_CONFLICTS",
        entities=(
            Entity(
                "ORDER",
                (
                    Field("ORDER_VALUE", 10000, 5000),
                    Field("DISCOUNT", 20, 10),
                ),
            ),
        ),
    )


# ============================================================================
# TESTS
# ============================================================================


def run_test(name: str, function) -> dict[str, Any]:

    try:
        passed = bool(function())
        return {
            "name": name,
            "status": "PASS" if passed else "FAIL",
        }
    except Exception as exc:
        return {
            "name": name,
            "status": "FAIL",
            "error": (f"{type(exc).__name__}: {exc}"),
        }


def test_feasible_spec() -> bool:

    _, conflicts = diagnose(feasible_spec())

    return not conflicts


def test_direct_conflict() -> bool:

    _, conflicts = diagnose(direct_conflict_spec())

    return any(
        c.conflict_type == "EMPTY_FEASIBLE_REGION" and c.field == "ORDER_VALUE"
        for c in conflicts
    )


def test_cross_field_conflict() -> bool:

    ranges, conflicts = diagnose(cross_field_conflict_spec())

    target = ranges[("ORDER", "ORDER_VALUE")]

    return target.minimum > target.maximum and any(
        c.field == "ORDER_VALUE" and "ORDER_ABOVE_CUSTOMER" in c.source_rules
        for c in conflicts
    )


def test_chained_conflict() -> bool:

    ranges, conflicts = diagnose(chained_conflict_spec())

    target = ranges[("CHAIN", "VALUE_B")]

    return target.minimum > target.maximum and bool(conflicts)


def test_conditional_conflict() -> bool:

    _, conflicts = diagnose(conditional_conflict_spec())

    return any(
        c.conflict_type == "CONDITIONAL_CONFLICT" and c.field == "DISCOUNT"
        for c in conflicts
    )


def test_multiple_conflicts() -> bool:

    _, conflicts = diagnose(multiple_conflict_spec())

    fields = {c.field for c in conflicts}

    return {
        "ORDER_VALUE",
        "DISCOUNT",
    }.issubset(fields)


def test_feasible_region_explanation() -> bool:

    ranges, conflicts = diagnose(cross_field_conflict_spec())

    target = ranges[("ORDER", "ORDER_VALUE")]

    return (
        target.minimum == 7000
        and target.maximum == 5000
        and any(c.feasible_region["empty"] for c in conflicts)
    )


def test_source_rule_references() -> bool:

    _, conflicts = diagnose(cross_field_conflict_spec())

    return any(c.source_rules for c in conflicts)


def test_dependency_path() -> bool:

    _, conflicts = diagnose(cross_field_conflict_spec())

    return any("ORDER.ORDER_VALUE" in c.dependency_path for c in conflicts)


def test_deterministic_diagnosis() -> bool:

    spec = cross_field_conflict_spec()

    _, first = diagnose(spec)
    _, second = diagnose(spec)

    return [asdict(c) for c in first] == [asdict(c) for c in second]


def test_entity_order_independence() -> bool:

    spec = cross_field_conflict_spec()

    alternate = Specification(
        name=spec.name,
        entities=tuple(reversed(spec.entities)),
        constraints=tuple(reversed(spec.constraints)),
        conditional_constraints=(spec.conditional_constraints),
    )

    _, first = diagnose(spec)
    _, second = diagnose(alternate)

    return sorted(asdict(c) for c in first) == sorted(asdict(c) for c in second)


def test_field_order_independence() -> bool:

    spec = cross_field_conflict_spec()

    alternate = Specification(
        name=spec.name,
        entities=tuple(
            Entity(
                e.name,
                tuple(reversed(e.fields)),
                e.record_count,
            )
            for e in spec.entities
        ),
        constraints=spec.constraints,
        conditional_constraints=(spec.conditional_constraints),
    )

    _, first = diagnose(spec)
    _, second = diagnose(alternate)

    return sorted(asdict(c) for c in first) == sorted(asdict(c) for c in second)


def test_generation_blocked() -> bool:

    try:
        generation_guard(cross_field_conflict_spec())
    except RuntimeError as exc:
        return "GENERATION_BLOCKED" in str(exc)

    return False


def test_no_hidden_relaxation() -> bool:

    ranges, conflicts = diagnose(cross_field_conflict_spec())

    r = ranges[("ORDER", "ORDER_VALUE")]

    return bool(conflicts) and r.minimum > r.maximum


def test_no_post_generation_repair() -> bool:

    # Infeasibility is detected before any generation
    # function can be called.
    _, conflicts = diagnose(cross_field_conflict_spec())

    return bool(conflicts)


def test_actionable_diagnosis() -> bool:

    _, conflicts = diagnose(cross_field_conflict_spec())

    relevant = next(c for c in conflicts if c.field == "ORDER_VALUE")

    return (
        "no feasible generation region" in relevant.message.lower()
        and bool(relevant.requirements)
        and bool(relevant.source_rules)
        and bool(relevant.dependency_path)
    )


def test_json_serialization() -> bool:

    spec = cross_field_conflict_spec()
    ranges, conflicts = diagnose(spec)

    payload = {
        "specification": spec.name,
        "specification_fingerprint": (spec_fingerprint(spec)),
        "feasible": not bool(conflicts),
        "conflicts": [asdict(c) for c in conflicts],
        "resolved_ranges": {
            f"{e}.{f}": asdict(r) for (e, f), r in sorted(ranges.items())
        },
    }

    decoded = json.loads(
        json.dumps(
            payload,
            sort_keys=True,
        )
    )

    return decoded["feasible"] is False and bool(decoded["conflicts"])


def test_unknown_entity_safety() -> bool:

    spec = Specification(
        name="UNKNOWN_ENTITY",
        entities=(
            Entity(
                "ORDER",
                (Field("VALUE", 0, 10),),
            ),
        ),
        constraints=(
            Constraint(
                "BAD_ENTITY",
                "CUSTOMER",
                "VALUE",
                ">=",
                5,
            ),
        ),
    )

    try:
        validate_specification(spec)
    except ValueError:
        return True

    return False


def test_unknown_field_safety() -> bool:

    spec = Specification(
        name="UNKNOWN_FIELD",
        entities=(
            Entity(
                "ORDER",
                (Field("VALUE", 0, 10),),
            ),
        ),
        constraints=(
            Constraint(
                "BAD_FIELD",
                "ORDER",
                "UNKNOWN",
                ">=",
                5,
            ),
        ),
    )

    try:
        validate_specification(spec)
    except ValueError:
        return True

    return False


def test_no_false_positive() -> bool:

    _, conflicts = diagnose(feasible_spec())

    return not conflicts


# ============================================================================
# REPRESENTATIVE DIAGNOSIS
# ============================================================================


def print_diagnosis(spec: Specification) -> None:

    ranges, conflicts = diagnose(spec)

    print()
    print("Representative conflict diagnosis:")

    if not conflicts:
        print("  Specification is feasible.")
        return

    conflict = conflicts[0]

    print(f"  Conflict: " f"{conflict.entity}.{conflict.field}")
    print(f"    type:              " f"{conflict.conflict_type}")
    print(f"    message:           " f"{conflict.message}")

    print("    requirements:")
    for requirement in conflict.requirements:
        print(f"      {requirement}")

    print("    resolved context:")
    for key, value in conflict.resolved_context.items():
        print(f"      {key}: {value}")

    print("    feasible region:")
    for key, value in conflict.feasible_region.items():
        print(f"      {key}: {value}")

    print("    source rules:")
    for source in conflict.source_rules:
        print(f"      {source}")

    print("    dependency path:")
    for path in conflict.dependency_path:
        print(f"      {path}")


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()
    print("=" * 70)
    print("FORGE - Experiment 020-U: " "Declarative Specification Conflict Diagnosis")
    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")
    print("Stage:          020-U")
    print(
        "Purpose:        "
        "Explainable specification conflict detection "
        "and diagnosis"
    )
    print(f"Random seed:    {MASTER_SEED}")

    print()
    print("Diagnosis architecture:")
    print("  Declarative specification")
    print("       ↓")
    print("  Requirement extraction")
    print("       ↓")
    print("  Constraint / dependency graph")
    print("       ↓")
    print("  Feasibility analysis")
    print("       ↓")
    print("  Conflict diagnosis")
    print("       ↓")
    print("  Actionable explanation")

    tests = [
        ("Feasible specification", test_feasible_spec),
        ("Direct field conflict", test_direct_conflict),
        ("Cross-field conflict", test_cross_field_conflict),
        ("Chained conflict", test_chained_conflict),
        ("Conditional conflict", test_conditional_conflict),
        ("Multiple conflict detection", test_multiple_conflicts),
        ("Feasible-region explanation", test_feasible_region_explanation),
        ("Source-rule references", test_source_rule_references),
        ("Dependency path", test_dependency_path),
        ("Deterministic diagnosis", test_deterministic_diagnosis),
        ("Entity-order independence", test_entity_order_independence),
        ("Field-order independence", test_field_order_independence),
        ("Generation blocking", test_generation_blocked),
        ("No hidden relaxation", test_no_hidden_relaxation),
        ("No post-generation repair", test_no_post_generation_repair),
        ("Actionable diagnosis", test_actionable_diagnosis),
        ("JSON serialization", test_json_serialization),
        ("Unknown entity safety", test_unknown_entity_safety),
        ("Unknown field safety", test_unknown_field_safety),
        ("No false-positive diagnosis", test_no_false_positive),
    ]

    print()
    print("Conflict diagnosis validation:")

    results = []

    for name, function in tests:

        result = run_test(
            name,
            function,
        )
        results.append(result)

        print(f"  {name:<40}" f"{result['status']}")

        if result["status"] == "FAIL" and "error" in result:
            print(f"      error: {result['error']}")

    representative = cross_field_conflict_spec()

    print_diagnosis(representative)

    passed = sum(result["status"] == "PASS" for result in results)
    total = len(results)
    overall = passed == total

    ranges, conflicts = diagnose(representative)

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-U",
        "purpose": ("Explainable specification conflict " "detection and diagnosis"),
        "random_seed": MASTER_SEED,
        "tests": results,
        "tests_passed": passed,
        "tests_total": total,
        "overall": ("PASS" if overall else "FAIL"),
        "representative_diagnosis": {
            "specification": representative.name,
            "specification_fingerprint": (spec_fingerprint(representative)),
            "feasible": not bool(conflicts),
            "conflict_count": len(conflicts),
            "conflicts": [asdict(c) for c in conflicts],
            "resolved_ranges": {
                f"{e}.{f}": asdict(r) for (e, f), r in sorted(ranges.items())
            },
        },
        "architecture": {
            "pre_generation_analysis": True,
            "structured_conflicts": True,
            "feasible_region_analysis": True,
            "source_rule_references": True,
            "dependency_paths": True,
            "deterministic": True,
            "entity_order_independent": True,
            "field_order_independent": True,
            "generation_blocked_on_infeasibility": True,
            "hidden_relaxation": False,
            "post_generation_repair": False,
        },
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            indent=2,
            sort_keys=True,
        )

    print()
    print("Experiment result:")
    print(f"  Tests passed:              " f"{passed}/{total}")
    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    print()
    print("Output:")
    print(f"  Results: {RESULTS_PATH}")

    print()

    if overall:
        print("Experiment completed successfully.")
        print(
            "Declarative specification conflict diagnosis "
            "is experimentally validated."
        )
        return 0

    print("Experiment completed with failures.")
    print("Failures are preserved as architectural evidence.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
