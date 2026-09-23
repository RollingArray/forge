export type ResultsArtifactType =
  | 'entity-files'
  | 'quality'
  | 'validation';

export interface ResultsCheckpointEntity {
  entity: string;
  target_rows: number;
  completed_chunks: number;
}

export interface ResultsCheckpoint {
  job_id: string;
  chunk_size: number;
  seed: number;
  schema_version: number;
  specification_hash: string;
  updated_at: string;
  entities: Record<string, ResultsCheckpointEntity>;
}

export interface ResultsQualityPerformance {
  available: boolean;
  elapsed_seconds: number;
  rows_per_second: number;
  total_generated_rows: number;
}

export interface ResultsQuality {
  population_fidelity: {
    difference: number;
    fidelity_rate: number;
    total_generated_rows: number;
    total_requested_rows: number;
  };
  performance: ResultsQualityPerformance;
  distribution_fidelity: {
    fields_analyzed: number;
  };
  statistical_fidelity: {
    numeric_fields_analyzed: number;
  };
  identity_space_utilization: {
    entities_analyzed: number;
  };
  relationship_fidelity: {
    relationships_analyzed: number;
  };
}

export interface ResultsValidation {
  valid: boolean;
  errors: unknown[];
  schema?: {
    entities_checked?: number;
    schema_valid_entities?: number;
    missing_schema_fields?: number;
    unexpected_fields?: number;
  };
  primary_keys?: {
    entities_checked?: number;
    duplicate_count?: number;
    rows_checked?: number;
  };
  completeness?: {
    fields_checked?: number;
    fields_without_missing?: number;
    missing_values?: number;
    rows_checked?: number;
  };
  foreign_keys?: {
    relationships_checked?: number;
  };
}

export interface ResultsEntity {
  index: number;
  name: string;
  targetRows: number;
  recordsGenerated: number;
  outputFile: string;
}

export interface ResultsArtifact {
  type: ResultsArtifactType;
  title: string;
  description: string;
  fileName?: string;
  available: boolean;
}

export interface ResultsViewModel {
  status: 'COMPLETED' | 'INCOMPLETE';
  jobId: string;
  updatedAt: string;
  entities: readonly ResultsEntity[];
  totalEntities: number;
  totalRecords: number;
  qualityReportAvailable: boolean;
  validationReportAvailable: boolean;
  generatedEntityFiles: number;
}
