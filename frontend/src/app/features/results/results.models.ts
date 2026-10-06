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
