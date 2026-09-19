"""Experiment 023 - FORGE Specification Execution."""

EXPERIMENT_NAME = "023 - FORGE Specification Execution"


def describe() -> str:
    """Return the purpose of this experiment."""

    return (
        "Consume a FORGE specification, plan population, generate "
        "synthetic data, and independently validate the result."
    )


if __name__ == "__main__":
    print(EXPERIMENT_NAME)
    print(describe())
