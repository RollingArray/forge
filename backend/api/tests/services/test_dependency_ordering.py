import pytest

from app.services.dependency_ordering import (
    DependencyCycleError,
    resolve_dependency_order,
)
from app.services.generation_planner import (
    ForeignKeyDependency,
    GenerationEntityPlan,
    GenerationPlan,
    GenerationPlanningError,
)


def test_parent_is_ordered_before_child():
    assert resolve_dependency_order(
        ["CHILD", "PARENT"],
        [("PARENT", "CHILD")],
    ) == ("PARENT", "CHILD")


def test_multi_level_dependencies_are_ordered():
    assert resolve_dependency_order(
        ["LEAF", "CHILD", "ROOT"],
        [("ROOT", "CHILD"), ("CHILD", "LEAF")],
    ) == ("ROOT", "CHILD", "LEAF")


def test_independent_entities_preserve_input_order():
    assert resolve_dependency_order(
        ["THIRD", "FIRST", "SECOND"],
        [],
    ) == ("THIRD", "FIRST", "SECOND")


def test_duplicate_dependency_edges_are_ignored():
    assert resolve_dependency_order(
        ["PARENT", "CHILD"],
        [("PARENT", "CHILD"), ("PARENT", "CHILD")],
    ) == ("PARENT", "CHILD")


def test_self_reference_is_a_cycle():
    with pytest.raises(DependencyCycleError) as exc_info:
        resolve_dependency_order(["ENTITY"], [("ENTITY", "ENTITY")])

    assert exc_info.value.unresolved_entities == ("ENTITY",)


def test_multi_entity_cycle_reports_unresolved_entities():
    with pytest.raises(DependencyCycleError) as exc_info:
        resolve_dependency_order(
            ["A", "B", "C"],
            [("A", "B"), ("B", "A"), ("B", "C")],
        )

    assert exc_info.value.unresolved_entities == ("A", "B", "C")


def test_unknown_dependency_entity_is_rejected():
    with pytest.raises(ValueError, match="unknown entity"):
        resolve_dependency_order(["PARENT"], [("PARENT", "MISSING")])


def test_duplicate_entity_names_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        resolve_dependency_order(["A", "A"], [])


def test_generation_order_preserves_existing_batch_order():
    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(entity_name="A", target_rows=1),
            GenerationEntityPlan(
                entity_name="B",
                target_rows=1,
                dependencies=(
                    ForeignKeyDependency(
                        foreign_key_name="FK_B_A",
                        parent_entity="A",
                        source_fields=("A_ID",),
                        target_fields=("ID",),
                    ),
                ),
            ),
            GenerationEntityPlan(entity_name="C", target_rows=1),
        )
    )

    assert plan.generation_order == ("A", "C", "B")


def test_generation_plan_translates_cycle_error():
    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="A",
                target_rows=1,
                dependencies=(
                    ForeignKeyDependency(
                        foreign_key_name="FK_A_B",
                        parent_entity="B",
                        source_fields=("B_ID",),
                        target_fields=("ID",),
                    ),
                ),
            ),
            GenerationEntityPlan(
                entity_name="B",
                target_rows=1,
                dependencies=(
                    ForeignKeyDependency(
                        foreign_key_name="FK_B_A",
                        parent_entity="A",
                        source_fields=("A_ID",),
                        target_fields=("ID",),
                    ),
                ),
            ),
        )
    )

    with pytest.raises(
        GenerationPlanningError,
        match="Possible dependency cycle involving",
    ):
        _ = plan.generation_order
