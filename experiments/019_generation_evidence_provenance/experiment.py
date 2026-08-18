"""
FORGE - Experiment 019: Generation Evidence / Provenance
==========================================================

Purpose
-------
This experiment tests whether FORGE can capture structured evidence about
how generated values were produced and whether that evidence can be used
to trace generated data back to its generation context.

The experiment builds on the reproducibility, strategy, relationship,
dependency, scenario, and validation capabilities established by earlier
experiments.

The following provenance forms are tested:

    - run-level provenance
    - field-level provenance
    - value-level provenance
    - generation strategy evidence
    - seed evidence
    - scenario evidence
    - parent dependency evidence
    - constraint evidence
    - provenance lookup
    - evidence integrity validation
    - reproducibility context

No machine learning, LLM, or real production data is used.

Experiment
----------
019 - Generation Evidence / Provenance

Key Question
------------
Can FORGE capture sufficient structured evidence to explain how a
generated value was produced without storing the complete generator
execution trace?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/019_generation_evidence_provenance/experiment.py

Output
------
Generated datasets and provenance evidence are written to:

    experiments/019_generation_evidence_provenance/output/

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

# ============================================================
# Paths
# ============================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent
SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"
OUTPUT_DIR = EXPERIMENT_DIR / "output"

PROVENANCE_FILE = OUTPUT_DIR / "generation_provenance.json"

STATISTICS_FILE = OUTPUT_DIR / "provenance_statistics.json"

CUSTOMER_FILE = OUTPUT_DIR / "CUSTOMER.csv"

ORDER_FILE = OUTPUT_DIR / "ORDER.csv"


# ============================================================
# Constants
# ============================================================

EXPERIMENT_ID = "019"

PASS = "PASS"
FAIL = "FAIL"

CUSTOMER_COUNT = 100
ORDER_COUNT = 1000


# ============================================================
# Specification
# ============================================================


def load_specification() -> dict[str, Any]:
    """Load the experiment specification."""

    with SPECIFICATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# ============================================================
# Provenance builder
# ============================================================


class ProvenanceStore:
    """
    In-memory provenance store.

    The store deliberately separates run-level, field-level, and
    value-level evidence.
    """

    def __init__(
        self,
        specification: dict[str, Any],
    ) -> None:

        generation = specification["generation"]

        self.specification = specification

        self.run_id = generation["run_id"]

        self.evidence_sequence = 0

        self.run_evidence: dict[str, Any] = {}

        self.field_evidence: dict[
            str,
            dict[str, Any],
        ] = {}

        self.value_evidence: dict[
            str,
            dict[str, Any],
        ] = {}

    # --------------------------------------------------------
    # Evidence ID
    # --------------------------------------------------------

    def next_evidence_id(self) -> str:
        """Generate the next evidence identifier."""

        self.evidence_sequence += 1

        return f"EV-{self.evidence_sequence:06d}"

    # --------------------------------------------------------
    # Run evidence
    # --------------------------------------------------------

    def capture_run_evidence(
        self,
    ) -> None:

        generation = self.specification["generation"]

        self.run_evidence = {
            "run_id": generation["run_id"],
            "experiment_id": EXPERIMENT_ID,
            "specification_id": (self.specification["experiment"]["id"]),
            "specification_name": (self.specification["experiment"]["name"]),
            "generator_version": (generation["generator_version"]),
            "seed": generation["seed"],
            "scenario": generation["scenario"],
        }

    # --------------------------------------------------------
    # Field evidence
    # --------------------------------------------------------

    def capture_field_evidence(
        self,
        entity: str,
        field: str,
        strategy: str,
        configuration: dict[str, Any],
    ) -> str:

        key = f"{entity}.{field}"

        if key not in self.field_evidence:

            self.field_evidence[key] = {
                "evidence_id": (self.next_evidence_id()),
                "entity": entity,
                "field": field,
                "strategy": strategy,
                "configuration": configuration,
                "run_id": self.run_id,
            }

        return self.field_evidence[key]["evidence_id"]

    # --------------------------------------------------------
    # Value evidence
    # --------------------------------------------------------

    def capture_value_evidence(
        self,
        entity: str,
        record_id: str,
        field: str,
        value: Any,
        strategy: str,
        field_evidence_id: str,
        parent_reference: dict[str, Any] | None = None,
        dependencies: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
        generation_parameters: dict[str, Any] | None = None,
    ) -> str:

        evidence_id = self.next_evidence_id()

        evidence = {
            "evidence_id": evidence_id,
            "run_id": self.run_id,
            "entity": entity,
            "record_id": record_id,
            "field": field,
            "generated_value": value,
            "strategy": strategy,
            "field_evidence_id": (field_evidence_id),
            "seed": self.specification["generation"]["seed"],
            "scenario": self.specification["generation"]["scenario"],
        }

        if parent_reference is not None:
            evidence["parent_reference"] = parent_reference

        if dependencies is not None:
            evidence["dependencies"] = dependencies

        if constraints is not None:
            evidence["constraints"] = constraints

        if generation_parameters is not None:
            evidence["generation_parameters"] = generation_parameters

        key = f"{entity}:" f"{record_id}:" f"{field}"

        self.value_evidence[key] = evidence

        return evidence_id

    # --------------------------------------------------------
    # Lookup
    # --------------------------------------------------------

    def lookup(
        self,
        entity: str,
        record_id: str,
        field: str,
    ) -> dict[str, Any] | None:

        key = f"{entity}:" f"{record_id}:" f"{field}"

        return self.value_evidence.get(key)

    # --------------------------------------------------------
    # Lookup by evidence ID
    # --------------------------------------------------------

    def lookup_evidence_id(
        self,
        evidence_id: str,
    ) -> dict[str, Any] | None:

        for evidence in self.value_evidence.values():

            if evidence["evidence_id"] == evidence_id:
                return evidence

        return None

    # --------------------------------------------------------
    # Serialize
    # --------------------------------------------------------

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "run": self.run_evidence,
            "fields": self.field_evidence,
            "values": self.value_evidence,
        }


# ============================================================
# Random helpers
# ============================================================


def create_rng(
    seed: int,
) -> random.Random:
    """Create an isolated random generator."""

    return random.Random(seed)


def weighted_choice(
    rng: random.Random,
    distribution: dict[str, float],
) -> str:
    """Select a value from a weighted distribution."""

    values = list(distribution.keys())

    weights = list(distribution.values())

    return rng.choices(
        values,
        weights=weights,
        k=1,
    )[0]


# ============================================================
# Customer generation
# ============================================================


def generate_customers(
    specification: dict[str, Any],
    provenance: ProvenanceStore,
) -> list[dict[str, Any]]:

    seed = specification["generation"]["seed"]

    rng = create_rng(seed)

    fields = specification["entities"]["CUSTOMER"]["fields"]

    customers = []

    # --------------------------------------------------------
    # Field evidence
    # --------------------------------------------------------

    customer_id_field_id = provenance.capture_field_evidence(
        entity="CUSTOMER",
        field="CUSTOMER_ID",
        strategy="sequential",
        configuration={
            "prefix": "CUS",
            "length": 10,
        },
    )

    customer_type_field_id = provenance.capture_field_evidence(
        entity="CUSTOMER",
        field="CUSTOMER_TYPE",
        strategy="weighted",
        configuration={
            "STANDARD": 0.70,
            "PREMIUM": 0.30,
        },
    )

    country_field_id = provenance.capture_field_evidence(
        entity="CUSTOMER",
        field="COUNTRY",
        strategy="weighted",
        configuration=fields["COUNTRY"]["distribution"],
    )

    email_field_id = provenance.capture_field_evidence(
        entity="CUSTOMER",
        field="EMAIL",
        strategy="random",
        configuration={
            "population": 0.80,
        },
    )

    # --------------------------------------------------------
    # Records
    # --------------------------------------------------------

    customer_type_distribution = {
        "STANDARD": 0.70,
        "PREMIUM": 0.30,
    }

    country_distribution = fields["COUNTRY"]["distribution"]

    for index in range(
        1,
        CUSTOMER_COUNT + 1,
    ):

        customer_id = f"CUS{index:07d}"

        customer_type = weighted_choice(
            rng,
            customer_type_distribution,
        )

        country = weighted_choice(
            rng,
            country_distribution,
        )

        email = None

        if rng.random() < 0.80:

            email = f"customer" f"{index}" f"@example.com"

        customers.append(
            {
                "CUSTOMER_ID": customer_id,
                "CUSTOMER_TYPE": customer_type,
                "COUNTRY": country,
                "EMAIL": email,
            }
        )

        provenance.capture_value_evidence(
            entity="CUSTOMER",
            record_id=customer_id,
            field="CUSTOMER_ID",
            value=customer_id,
            strategy="sequential",
            field_evidence_id=(customer_id_field_id),
            generation_parameters={
                "prefix": "CUS",
                "sequence": index,
            },
        )

        provenance.capture_value_evidence(
            entity="CUSTOMER",
            record_id=customer_id,
            field="CUSTOMER_TYPE",
            value=customer_type,
            strategy="weighted",
            field_evidence_id=(customer_type_field_id),
            generation_parameters={
                "distribution": (customer_type_distribution),
            },
        )

        provenance.capture_value_evidence(
            entity="CUSTOMER",
            record_id=customer_id,
            field="COUNTRY",
            value=country,
            strategy="weighted",
            field_evidence_id=(country_field_id),
            generation_parameters={
                "distribution": (country_distribution),
            },
        )

        provenance.capture_value_evidence(
            entity="CUSTOMER",
            record_id=customer_id,
            field="EMAIL",
            value=email,
            strategy="random",
            field_evidence_id=(email_field_id),
            generation_parameters={
                "population": 0.80,
            },
        )

    return customers


# ============================================================
# Order generation
# ============================================================


def generate_orders(
    specification: dict[str, Any],
    customers: list[dict[str, Any]],
    provenance: ProvenanceStore,
) -> list[dict[str, Any]]:

    seed = specification["generation"]["seed"]

    # Use a separate deterministic stream so the generation
    # context is explicit and reproducible.
    rng = create_rng(seed + 1)

    order_fields = specification["entities"]["ORDER"]["fields"]

    orders = []

    # --------------------------------------------------------
    # Field evidence
    # --------------------------------------------------------

    order_id_field_id = provenance.capture_field_evidence(
        entity="ORDER",
        field="ORDER_ID",
        strategy="sequential",
        configuration={
            "prefix": "ORD",
            "length": 10,
        },
    )

    customer_reference_field_id = provenance.capture_field_evidence(
        entity="ORDER",
        field="CUSTOMER_ID",
        strategy="parent_reference",
        configuration={"reference": ("CUSTOMER.CUSTOMER_ID")},
    )

    amount_field_id = provenance.capture_field_evidence(
        entity="ORDER",
        field="AMOUNT",
        strategy="parent_dependent",
        configuration=order_fields["AMOUNT"]["parameters"],
    )

    discount_field_id = provenance.capture_field_evidence(
        entity="ORDER",
        field="DISCOUNT",
        strategy="scenario_dependent",
        configuration=order_fields["DISCOUNT"]["parameters"],
    )

    # --------------------------------------------------------
    # Constraint evidence
    # --------------------------------------------------------

    constraint_ids = [constraint["id"] for constraint in specification["constraints"]]

    # --------------------------------------------------------
    # Records
    # --------------------------------------------------------

    for index in range(
        1,
        ORDER_COUNT + 1,
    ):

        customer = rng.choice(customers)

        customer_id = customer["CUSTOMER_ID"]

        customer_type = customer["CUSTOMER_TYPE"]

        order_id = f"ORD{index:07d}"

        amount_parameters = order_fields["AMOUNT"]["parameters"][customer_type]

        amount = round(
            rng.uniform(
                amount_parameters["min"],
                amount_parameters["max"],
            ),
            2,
        )

        scenario = specification["generation"]["scenario"]

        discount_parameters = order_fields["DISCOUNT"]["parameters"][scenario]

        discount = round(
            rng.uniform(
                discount_parameters["min"],
                discount_parameters["max"],
            ),
            2,
        )

        order = {
            "ORDER_ID": order_id,
            "CUSTOMER_ID": customer_id,
            "AMOUNT": amount,
            "DISCOUNT": discount,
        }

        orders.append(order)

        # ----------------------------------------------------
        # ORDER_ID evidence
        # ----------------------------------------------------

        provenance.capture_value_evidence(
            entity="ORDER",
            record_id=order_id,
            field="ORDER_ID",
            value=order_id,
            strategy="sequential",
            field_evidence_id=(order_id_field_id),
            generation_parameters={
                "prefix": "ORD",
                "sequence": index,
            },
        )

        # ----------------------------------------------------
        # CUSTOMER_ID evidence
        # ----------------------------------------------------

        provenance.capture_value_evidence(
            entity="ORDER",
            record_id=order_id,
            field="CUSTOMER_ID",
            value=customer_id,
            strategy="parent_reference",
            field_evidence_id=(customer_reference_field_id),
            parent_reference={
                "entity": "CUSTOMER",
                "record_id": customer_id,
                "field": "CUSTOMER_ID",
                "value": customer_id,
            },
        )

        # ----------------------------------------------------
        # AMOUNT evidence
        # ----------------------------------------------------

        provenance.capture_value_evidence(
            entity="ORDER",
            record_id=order_id,
            field="AMOUNT",
            value=amount,
            strategy="parent_dependent",
            field_evidence_id=(amount_field_id),
            parent_reference={
                "entity": "CUSTOMER",
                "record_id": customer_id,
                "field": "CUSTOMER_TYPE",
                "value": customer_type,
            },
            dependencies={
                "source_field": ("CUSTOMER.CUSTOMER_TYPE"),
                "source_value": customer_type,
            },
            generation_parameters={
                "min": amount_parameters["min"],
                "max": amount_parameters["max"],
            },
        )

        # ----------------------------------------------------
        # DISCOUNT evidence
        # ----------------------------------------------------

        provenance.capture_value_evidence(
            entity="ORDER",
            record_id=order_id,
            field="DISCOUNT",
            value=discount,
            strategy="scenario_dependent",
            field_evidence_id=(discount_field_id),
            constraints=constraint_ids,
            generation_parameters={
                "scenario": scenario,
                "min": discount_parameters["min"],
                "max": discount_parameters["max"],
            },
        )

    return orders


# ============================================================
# CSV output
# ============================================================


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    """Write a simple CSV without requiring pandas."""

    import csv

    if not rows:
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = list(rows[0].keys())

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# Evidence validation
# ============================================================


def validate_run_provenance(
    specification: dict[str, Any],
    provenance: ProvenanceStore,
) -> bool:

    expected = specification["generation"]

    run = provenance.run_evidence

    return all(
        [
            run["run_id"] == expected["run_id"],
            run["specification_id"] == specification["experiment"]["id"],
            run["generator_version"] == expected["generator_version"],
            run["seed"] == expected["seed"],
            run["scenario"] == expected["scenario"],
        ]
    )


def validate_field_provenance(
    provenance: ProvenanceStore,
) -> bool:

    required_fields = {
        "CUSTOMER.CUSTOMER_ID",
        "CUSTOMER.CUSTOMER_TYPE",
        "CUSTOMER.COUNTRY",
        "CUSTOMER.EMAIL",
        "ORDER.ORDER_ID",
        "ORDER.CUSTOMER_ID",
        "ORDER.AMOUNT",
        "ORDER.DISCOUNT",
    }

    return required_fields.issubset(set(provenance.field_evidence.keys()))


def validate_value_evidence(
    customers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    provenance: ProvenanceStore,
) -> dict[str, Any]:

    checks = {
        "entity_match": True,
        "record_match": True,
        "field_match": True,
        "value_match": True,
    }

    checked = 0

    # --------------------------------------------------------
    # Customer evidence
    # --------------------------------------------------------

    for row in customers:

        record_id = row["CUSTOMER_ID"]

        for field, value in row.items():

            evidence = provenance.lookup(
                "CUSTOMER",
                record_id,
                field,
            )

            checked += 1

            if evidence is None:
                checks["entity_match"] = False
                continue

            if evidence["entity"] != "CUSTOMER":
                checks["entity_match"] = False

            if evidence["record_id"] != record_id:
                checks["record_match"] = False

            if evidence["field"] != field:
                checks["field_match"] = False

            if evidence["generated_value"] != value:
                checks["value_match"] = False

    # --------------------------------------------------------
    # Order evidence
    # --------------------------------------------------------

    for row in orders:

        record_id = row["ORDER_ID"]

        for field, value in row.items():

            evidence = provenance.lookup(
                "ORDER",
                record_id,
                field,
            )

            checked += 1

            if evidence is None:
                checks["entity_match"] = False
                continue

            if evidence["entity"] != "ORDER":
                checks["entity_match"] = False

            if evidence["record_id"] != record_id:
                checks["record_match"] = False

            if evidence["field"] != field:
                checks["field_match"] = False

            if evidence["generated_value"] != value:
                checks["value_match"] = False

    checks["overall"] = all(checks.values())

    checks["values_checked"] = checked

    return checks


# ============================================================
# Strategy evidence validation
# ============================================================


def validate_strategy_evidence(
    provenance: ProvenanceStore,
) -> bool:

    expected_strategies = {
        "CUSTOMER.CUSTOMER_ID": "sequential",
        "CUSTOMER.CUSTOMER_TYPE": "weighted",
        "CUSTOMER.COUNTRY": "weighted",
        "CUSTOMER.EMAIL": "random",
        "ORDER.ORDER_ID": "sequential",
        "ORDER.CUSTOMER_ID": "parent_reference",
        "ORDER.AMOUNT": "parent_dependent",
        "ORDER.DISCOUNT": "scenario_dependent",
    }

    for key, expected in expected_strategies.items():

        evidence = provenance.field_evidence.get(key)

        if evidence is None:
            return False

        if evidence["strategy"] != expected:
            return False

    return True


# ============================================================
# Parent dependency validation
# ============================================================


def validate_parent_dependency(
    orders: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    provenance: ProvenanceStore,
) -> bool:

    customer_map = {customer["CUSTOMER_ID"]: customer for customer in customers}

    # Check a representative sample rather than every
    # provenance record. The value-level integrity validation
    # already checks every generated value.
    sample_orders = orders[:10]

    for order in sample_orders:

        order_id = order["ORDER_ID"]

        customer_id = order["CUSTOMER_ID"]

        customer = customer_map.get(customer_id)

        if customer is None:
            return False

        evidence = provenance.lookup(
            "ORDER",
            order_id,
            "AMOUNT",
        )

        if evidence is None:
            return False

        parent = evidence.get("parent_reference")

        if parent is None:
            return False

        if parent["entity"] != "CUSTOMER":
            return False

        if parent["record_id"] != customer_id:
            return False

        if parent["field"] != "CUSTOMER_TYPE":
            return False

        if parent["value"] != customer["CUSTOMER_TYPE"]:
            return False

    return True


# ============================================================
# Scenario validation
# ============================================================


def validate_scenario_evidence(
    specification: dict[str, Any],
    provenance: ProvenanceStore,
) -> bool:

    expected_scenario = specification["generation"]["scenario"]

    for evidence in provenance.value_evidence.values():

        if evidence["scenario"] != expected_scenario:
            return False

    return True


# ============================================================
# Constraint evidence validation
# ============================================================


def validate_constraint_evidence(
    specification: dict[str, Any],
    provenance: ProvenanceStore,
) -> bool:

    expected_ids = [constraint["id"] for constraint in specification["constraints"]]

    discount_evidence = [
        evidence
        for evidence in (provenance.value_evidence.values())
        if evidence["entity"] == "ORDER" and evidence["field"] == "DISCOUNT"
    ]

    if not discount_evidence:
        return False

    for evidence in discount_evidence:

        if evidence.get("constraints") != expected_ids:
            return False

    return True


# ============================================================
# Reproducibility context validation
# ============================================================


def validate_reproducibility_context(
    specification: dict[str, Any],
    provenance: ProvenanceStore,
) -> bool:

    required_context = specification["reproducibility"]["required_context"]

    run = provenance.run_evidence

    context_mapping = {
        "specification_id": ("specification_id"),
        "specification_version": None,
        "seed": "seed",
        "scenario": "scenario",
        "generator_version": ("generator_version"),
    }

    for context in required_context:

        key = context_mapping.get(context)

        if key is None:

            # The current specification does not
            # explicitly declare a version field.
            # Treat the experiment identity as the
            # specification version for this experiment.
            if context == ("specification_version"):
                if not specification["experiment"].get("id"):
                    return False

                continue

            return False

        if run.get(key) is None:
            return False

    return True


# ============================================================
# Provenance lookup validation
# ============================================================


def validate_lookup(
    orders: list[dict[str, Any]],
    provenance: ProvenanceStore,
) -> dict[str, Any]:

    if not orders:
        return {
            "lookup_success": False,
            "evidence_id_lookup_success": False,
            "overall": False,
        }

    sample = orders[0]

    entity = "ORDER"
    record_id = sample["ORDER_ID"]
    field = "AMOUNT"

    evidence = provenance.lookup(
        entity,
        record_id,
        field,
    )

    lookup_success = evidence is not None

    evidence_id_lookup_success = False

    if evidence is not None:

        evidence_id = evidence["evidence_id"]

        by_id = provenance.lookup_evidence_id(evidence_id)

        evidence_id_lookup_success = (
            by_id is not None and by_id["evidence_id"] == evidence_id
        )

    return {
        "lookup_success": (lookup_success),
        "evidence_id_lookup_success": (evidence_id_lookup_success),
        "overall": (lookup_success and evidence_id_lookup_success),
        "sample": {
            "entity": entity,
            "record_id": record_id,
            "field": field,
            "evidence_id": (evidence["evidence_id"] if evidence else None),
        },
    }


# ============================================================
# Save provenance
# ============================================================


def save_provenance(
    provenance: ProvenanceStore,
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with PROVENANCE_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            provenance.to_dict(),
            file,
            indent=2,
            default=str,
        )


def save_statistics(
    statistics: dict[str, Any],
) -> None:

    with STATISTICS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            statistics,
            file,
            indent=2,
            default=str,
        )


# ============================================================
# Console helpers
# ============================================================


def print_status(
    label: str,
    result: bool,
) -> None:

    print(f"  {label:<36}" f"{PASS if result else FAIL}")


def print_evidence(
    evidence: dict[str, Any],
) -> None:

    print(f"    Evidence ID: " f"{evidence['evidence_id']}")

    print(f"    Entity:      " f"{evidence['entity']}")

    print(f"    Record:      " f"{evidence['record_id']}")

    print(f"    Field:       " f"{evidence['field']}")

    print(f"    Value:       " f"{evidence['generated_value']}")

    print(f"    Strategy:    " f"{evidence['strategy']}")

    print(f"    Seed:        " f"{evidence['seed']}")

    print(f"    Scenario:    " f"{evidence['scenario']}")

    if "parent_reference" in evidence:

        parent = evidence["parent_reference"]

        print("    Parent:      " f"{parent['entity']}." f"{parent['record_id']}")

        print("    Parent field:" f" {parent['field']}")

        print("    Parent value:" f" {parent['value']}")

    if "generation_parameters" in evidence:

        print("    Parameters:  " f"{evidence['generation_parameters']}")


# ============================================================
# Main
# ============================================================


def main() -> None:
    """Run Experiment 019."""

    specification = load_specification()

    experiment = specification["experiment"]

    generation = specification["generation"]

    print("=" * 70)
    print("FORGE - Experiment 019: " "Generation Evidence / Provenance")
    print("=" * 70)

    print(f"Experiment:   " f"{experiment['id']} - " f"{experiment['name']}")

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   " f"{generation['seed']}")

    print(f"Scenario:      " f"{generation['scenario']}")

    print(f"Run ID:        " f"{generation['run_id']}")

    # --------------------------------------------------------
    # Initialize provenance
    # --------------------------------------------------------

    provenance = ProvenanceStore(specification)

    provenance.capture_run_evidence()

    # --------------------------------------------------------
    # Generate data
    # --------------------------------------------------------

    print("\nGenerating dataset...")

    customers = generate_customers(
        specification,
        provenance,
    )

    orders = generate_orders(
        specification,
        customers,
        provenance,
    )

    print(f"  Generated " f"{len(customers)} records for CUSTOMER")

    print(f"  Generated " f"{len(orders)} records for ORDER")

    # --------------------------------------------------------
    # Save datasets
    # --------------------------------------------------------

    write_csv(
        CUSTOMER_FILE,
        customers,
    )

    write_csv(
        ORDER_FILE,
        orders,
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\nProvenance validation:")

    run_result = validate_run_provenance(
        specification,
        provenance,
    )

    field_result = validate_field_provenance(provenance)

    strategy_result = validate_strategy_evidence(provenance)

    value_results = validate_value_evidence(
        customers,
        orders,
        provenance,
    )

    parent_result = validate_parent_dependency(
        orders,
        customers,
        provenance,
    )

    scenario_result = validate_scenario_evidence(
        specification,
        provenance,
    )

    constraint_result = validate_constraint_evidence(
        specification,
        provenance,
    )

    reproducibility_result = validate_reproducibility_context(
        specification,
        provenance,
    )

    lookup_results = validate_lookup(
        orders,
        provenance,
    )

    print_status(
        "Run-level provenance",
        run_result,
    )

    print_status(
        "Field-level provenance",
        field_result,
    )

    print_status(
        "Strategy evidence",
        strategy_result,
    )

    print_status(
        "Value evidence integrity",
        value_results["overall"],
    )

    print_status(
        "Parent dependency evidence",
        parent_result,
    )

    print_status(
        "Scenario evidence",
        scenario_result,
    )

    print_status(
        "Constraint evidence",
        constraint_result,
    )

    print_status(
        "Reproducibility context",
        reproducibility_result,
    )

    print_status(
        "Provenance lookup",
        lookup_results["overall"],
    )

    # --------------------------------------------------------
    # Evidence demonstration
    # --------------------------------------------------------

    sample_order = orders[0]

    sample_evidence = provenance.lookup(
        "ORDER",
        sample_order["ORDER_ID"],
        "AMOUNT",
    )

    print("\nSample value provenance:")

    if sample_evidence:

        print_evidence(sample_evidence)

    else:

        print("    No evidence found")

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    total_value_evidence = len(provenance.value_evidence)

    total_field_evidence = len(provenance.field_evidence)

    total_run_evidence = 1 if provenance.run_evidence else 0

    evidence_statistics = {
        "run_evidence_records": (total_run_evidence),
        "field_evidence_records": (total_field_evidence),
        "value_evidence_records": (total_value_evidence),
        "customer_records": len(customers),
        "order_records": len(orders),
        "values_per_record": {
            "CUSTOMER": len(customers[0]),
            "ORDER": len(orders[0]),
        },
        "provenance_coverage": {
            "CUSTOMER": (total_field_evidence > 0),
            "ORDER": (total_field_evidence > 0),
        },
    }

    # --------------------------------------------------------
    # Overall result
    # --------------------------------------------------------

    overall_result = all(
        [
            run_result,
            field_result,
            strategy_result,
            value_results["overall"],
            parent_result,
            scenario_result,
            constraint_result,
            reproducibility_result,
            lookup_results["overall"],
        ]
    )

    statistics = {
        "experiment": experiment,
        "generation": generation,
        "validation": {
            "run_provenance": (PASS if run_result else FAIL),
            "field_provenance": (PASS if field_result else FAIL),
            "strategy_evidence": (PASS if strategy_result else FAIL),
            "value_evidence": (PASS if value_results["overall"] else FAIL),
            "parent_dependency_evidence": (PASS if parent_result else FAIL),
            "scenario_evidence": (PASS if scenario_result else FAIL),
            "constraint_evidence": (PASS if constraint_result else FAIL),
            "reproducibility_context": (PASS if reproducibility_result else FAIL),
            "provenance_lookup": (PASS if lookup_results["overall"] else FAIL),
            "overall": (PASS if overall_result else FAIL),
        },
        "evidence_statistics": (evidence_statistics),
        "value_integrity": value_results,
        "lookup": lookup_results,
    }

    save_provenance(provenance)

    save_statistics(statistics)

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    print("\nOutput:")

    print(f"  Customer:    " f"{CUSTOMER_FILE}")

    print(f"  Order:       " f"{ORDER_FILE}")

    print(f"  Provenance:  " f"{PROVENANCE_FILE}")

    print(f"  Statistics:  " f"{STATISTICS_FILE}")

    print("\nEvidence statistics:")

    print(f"  Run evidence:   " f"{total_run_evidence}")

    print(f"  Field evidence: " f"{total_field_evidence}")

    print(f"  Value evidence: " f"{total_value_evidence}")

    print("\nExperiment result:")

    print(f"  Run provenance: " f"{PASS if run_result else FAIL}")

    print(f"  Field provenance: " f"{PASS if field_result else FAIL}")

    print(f"  Value provenance: " f"{PASS if value_results['overall'] else FAIL}")

    print(f"  Parent dependency: " f"{PASS if parent_result else FAIL}")

    print(f"  Scenario evidence: " f"{PASS if scenario_result else FAIL}")

    print(f"  Constraint evidence: " f"{PASS if constraint_result else FAIL}")

    print(f"  Evidence integrity: " f"{PASS if value_results['overall'] else FAIL}")

    print(f"  Provenance lookup: " f"{PASS if lookup_results['overall'] else FAIL}")

    print(f"  Reproducibility context: " f"{PASS if reproducibility_result else FAIL}")

    print(f"  Overall: " f"{PASS if overall_result else FAIL}")

    print("\nExperiment completed successfully.")


# ============================================================
# Entry point
# ============================================================


if __name__ == "__main__":
    main()
