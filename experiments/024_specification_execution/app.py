"""
FORGE Generation Core
Console demonstration consuming the Experiment 022 specification.
"""

import importlib.util
import json
import sys
import types
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent
EXPERIMENTS_ROOT = EXPERIMENT_ROOT.parent
BASE = EXPERIMENT_ROOT / "generation"

SPECIFICATION_PATH = (
    EXPERIMENTS_ROOT
    / "022_llm_assisted_specification_authoring"
    / "output"
    / "specification.json"
)

VALIDATION_OUTPUT_DIRECTORY = EXPERIMENT_ROOT / "output" / "validation"
QUALITY_OUTPUT_DIRECTORY = EXPERIMENT_ROOT / "output" / "quality"

PACKAGE_NAME = "forge_generation_console"


package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(BASE)]
sys.modules[PACKAGE_NAME] = package


def load_module(name: str):
    """Load one generation module under the synthetic package."""

    path = BASE / f"{name}.py"
    module_name = f"{PACKAGE_NAME}.{name}"

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return module


load_module("result")
load_module("chunking")
load_module("semantic")
progress_module = load_module("progress")
load_module("generator")
validator = load_module("validator")
quality = load_module("quality")
job_module = load_module("job")
planner = load_module("planner")
executor = load_module("executor")
specification_module = load_module("specification")


def main() -> None:
    """Load the real Experiment 022 specification and generate data."""

    specification = specification_module.load_specification(SPECIFICATION_PATH)

    plan = planner.build_generation_plan(specification)

    job = job_module.create_generation_job(specification_path=str(SPECIFICATION_PATH))

    planner.initialize_job_progress(
        job,
        plan,
    )

    print()
    print("=" * 70)
    print("FORGE GENERATION")
    print("=" * 70)
    print(f"Specification : {SPECIFICATION_PATH}")
    print(f"Job           : {job.job_id}")
    print(f"Entities      : {len(plan.entities)}")
    print(f"Target rows   : {plan.total_target_rows}")
    print(f"Status        : {job.status}")
    print()

    output_directory = BASE.parent / "output" / "generated" / job.job_id

    progress_reporter = progress_module.CLIProgressReporter(
        total_target_rows=plan.total_target_rows,
    )

    result = executor.execute_generation_plan(
        specification=specification,
        job=job,
        plan=plan,
        seed=42,
        chunk_size=1000,
        output_directory=str(output_directory),
        progress_reporter=progress_reporter,
    )

    print(f"Output        : {output_directory}")

    print("ENTITY RESULTS")
    print("-" * 70)

    for entity_name, progress in result.entities.items():
        print(
            f"{entity_name:20}"
            f"{progress.generated_rows:>8}/"
            f"{progress.target_rows:<8}"
            f"{progress.status.value}"
        )

    print()
    print(f"Total generated : {result.total_generated_rows}")
    print(f"Progress        : {result.progress:.1%}")
    print(f"Final status    : {result.status.value}")
    print(f"Error           : {result.error}")
    print("=" * 70)

    if result.status.value == "COMPLETED":

        validation_evidence = validator.ValidationEvidence()

        validation_errors = validator.validate_dataset(
            specification=specification,
            output_directory=output_directory,
            evidence=validation_evidence,
        )

        print()
        print("=" * 70)
        print("FORGE DATASET VALIDATION")
        print("=" * 70)
        print(f"Specification : {SPECIFICATION_PATH}")
        print(f"Dataset       : {output_directory}")
        print()

        validation_report = validator.build_validation_report(
            job_id=job.job_id,
            specification_path=SPECIFICATION_PATH,
            output_directory=output_directory,
            evidence=validation_evidence,
            errors=validation_errors,
        )

        validation_output_directory = VALIDATION_OUTPUT_DIRECTORY
        validation_output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        validation_path = (
            validation_output_directory
            / f"{job.job_id}_validation.json"
        )

        validator.write_validation_report(
            report=validation_report,
            output_path=validation_path,
        )

        if validation_errors:
            print(
                f"VALIDATION FAILED — "
                f"{len(validation_errors)} issue(s)"
            )
            print("-" * 70)

            for error in validation_errors:
                print(error)

        else:
            print("VALIDATION PASSED")
            print("Identity uniqueness : PASS")
            print("Foreign keys        : PASS")
            print("Constraints         : PASS")

            quality_output_directory = QUALITY_OUTPUT_DIRECTORY
            quality_output_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            quality_profile = quality.build_quality_profile(
                specification=specification,
                output_directory=output_directory,
                validation_evidence=validation_evidence.to_dict(),
                generation_result=result,
                generation_plan=plan,
            )

            quality_profile = {
                "job_id": job.job_id,
                "specification": str(SPECIFICATION_PATH),
                "dataset": str(output_directory),
                "quality": quality_profile,
            }

            quality_path = (
                quality_output_directory
                / f"{job.job_id}_quality.json"
            )

            quality_path.write_text(
                json.dumps(
                    quality_profile,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            print()
            print("FORGE QUALITY PROFILE")
            print("-" * 70)
            print(f"Quality profile : {quality_path}")
            print("Quality analysis: COMPLETED")

        print()
        print(f"Validation report : {validation_path}")
        print("=" * 70)

    else:
        print()
        print("=" * 70)
        print("FORGE DATASET VALIDATION")
        print("=" * 70)
        print("Validation skipped because generation did not complete.")
        print("=" * 70)


if __name__ == "__main__":
    main()
