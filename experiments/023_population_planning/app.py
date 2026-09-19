"""Application entry point for Experiment 023."""

from pathlib import Path

from population.console import (
    build_plan_from_specification,
    load_specification,
    print_population_analysis,
    write_population_plan,
)
from population.planner import has_infeasible_plan


EXPERIMENT_ROOT = Path(__file__).resolve().parent
EXPERIMENTS_ROOT = EXPERIMENT_ROOT.parent

SPECIFICATION_PATH = (
    EXPERIMENTS_ROOT
    / "022_llm_assisted_specification_authoring"
    / "output"
    / "specification.json"
)

OUTPUT_PATH = (
    EXPERIMENT_ROOT
    / "output"
    / "population_plan.json"
)


def main() -> None:
    """Run Experiment 023 population planning."""

    print("FORGE POPULATION PLANNING")
    print(f"Specification : {SPECIFICATION_PATH}")
    print(f"Exists        : {SPECIFICATION_PATH.exists()}")
    print()

    if not SPECIFICATION_PATH.exists():
        raise FileNotFoundError(
            f"Specification not found: {SPECIFICATION_PATH}"
        )

    specification = load_specification(
        SPECIFICATION_PATH
    )

    plan = build_plan_from_specification(
        specification
    )

    print_population_analysis(plan)

    output_path = write_population_plan(
        plan=plan,
        path=OUTPUT_PATH,
    )

    print()
    print(f"Population plan : {output_path}")

    if has_infeasible_plan(plan):
        print("Population plan status: INFEASIBLE")
    else:
        print("Population plan status: FEASIBLE")


if __name__ == "__main__":
    main()
