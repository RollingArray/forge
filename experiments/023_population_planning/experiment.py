"""Experiment 023 - FORGE Population Planning."""

EXPERIMENT_NAME = "023 - FORGE Population Planning"


def describe() -> str:
    """Return the purpose of this experiment."""

    return (
        "Analyze requested entity populations against the relational "
        "constraints defined by a FORGE specification."
    )


if __name__ == "__main__":
    print(EXPERIMENT_NAME)
    print(describe())
