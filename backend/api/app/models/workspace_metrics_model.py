from pydantic import BaseModel


class WorkspaceMetricsModel(BaseModel):
    total_data_models: int
    total_entities: int
    generated_datasets: int
    total_records: int
