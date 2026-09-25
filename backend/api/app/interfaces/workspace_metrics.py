from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceMetrics:
    total_data_models: int
    total_entities: int
    generated_datasets: int
    total_records: int
