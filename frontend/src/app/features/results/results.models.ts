export interface GenerationArtifact {
  entity_name: string;
  filename: string;
  rows: number;
  size_bytes: number;
}

export interface GenerationArtifactPreview {
  entity_name: string;
  filename: string;
  columns: string[];
  rows: Record<string, string | null>[];
  total_rows: number;
  preview_rows: number;
}


export interface GenerationQualityProfile {
  population_fidelity: Record<string, unknown>;
  distribution_fidelity: Record<string, unknown>;
  relationship_fidelity: Record<string, unknown>;
  identity_space_utilization: Record<string, unknown>;
  statistical_fidelity: Record<string, unknown>;
  performance: Record<string, unknown>;
  validation: Record<string, unknown>;
}



export interface GenerationQualityMetricSummary {
  value: number | null;
  measurement_status: string;
}

export interface GenerationQualitySummary {
  data_model_id: string;
  job_id: string;
  population_fidelity: GenerationQualityMetricSummary;
  relationship_count: GenerationQualityMetricSummary;
  distribution_count: GenerationQualityMetricSummary;
  statistical_count: GenerationQualityMetricSummary;
  throughput: GenerationQualityMetricSummary;
  identity_count: GenerationQualityMetricSummary;
}

export interface GenerationValidationSummary {
  valid: boolean;
  entity_count: number;
  expected_rows: number;
  generated_rows: number;
  error_count: number;
  errors: string[];
  warnings: string[];
  evidence: Record<string, unknown>;
}


export interface GenerationValidationSummaryResponse {
  data_model_id: string;
  job_id: string;
  valid: boolean | null;
  rows_validated: number;
  expected_rows: number;
  entities_checked: number;
  relationships_checked: number;
  constraints_checked: number;
  error_count: number;
  warning_count: number;
}


export interface GenerationArtifactDataPage {
  entity_name: string;
  filename: string;
  columns: string[];
  rows: Record<string, string | null>[];
  total_rows: number;
  offset: number;
  limit: number;
  search: string;
}
