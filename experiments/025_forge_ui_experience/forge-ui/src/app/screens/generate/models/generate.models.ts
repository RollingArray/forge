export type GenerationRunStatus =
  | 'COMPLETED'
  | 'IN_PROGRESS'
  | 'PARTIAL'
  | 'FAILED';

export interface GenerationCheckpointEntity {
  readonly completed_chunks: readonly number[];
  readonly target_rows: number;
}

export interface GenerationCheckpoint {
  readonly chunk_size: number;
  readonly entities: Record<string, GenerationCheckpointEntity>;
  readonly job_id: string;
  readonly schema_version: number;
  readonly seed: number;
  readonly specification_hash: string;
  readonly updated_at: string;
}

export interface GenerationQuality {
  readonly population_fidelity: {
    readonly difference: number;
    readonly fidelity_rate: number;
    readonly total_generated_rows: number;
    readonly total_requested_rows: number;
    readonly entities: Record<string, {
      readonly difference: number;
      readonly fidelity_rate: number;
      readonly generated_rows: number;
      readonly requested_rows: number;
    }>;
  };
  readonly performance: {
    readonly available: boolean;
    readonly elapsed_seconds: number | null;
    readonly rows_per_second: number | null;
    readonly total_generated_rows: number;
  };
  readonly distribution_fidelity: {
    readonly fields_analyzed: number;
  };
  readonly statistical_fidelity: {
    readonly numeric_fields_analyzed: number;
  };
  readonly identity_space_utilization: {
    readonly entities_analyzed: number;
  };
  readonly relationship_fidelity: {
    readonly relationships_analyzed: number;
  };
  readonly validation: Record<string, unknown>;
}

export interface GenerationValidation {
  readonly dataset: string;
  readonly errors: readonly unknown[];
  readonly job_id: string;
  readonly specification: string;
  readonly valid: boolean;
  readonly validation: Record<string, unknown>;
}

export interface GenerationArtifacts {
  readonly checkpoint: GenerationCheckpoint;
  readonly quality: GenerationQuality;
  readonly validation: GenerationValidation;
}

export interface EntityGenerationRow {
  readonly entity: string;
  readonly plannedRows: number;
  readonly generatedRows: number;
  readonly progress: number;
  readonly completedChunks: number;
  readonly totalChunks: number;
  readonly status: GenerationRunStatus;
}

export interface GenerationPipelineStage {
  readonly id:
    | 'load-specification'
    | 'initialize-plan'
    | 'generate-data'
    | 'validate'
    | 'quality'
    | 'finalize';
  readonly label: string;
  readonly status: 'COMPLETED' | 'PENDING';
}

export interface GenerationQualityMetric {
  readonly label: string;
  readonly value: string;
  readonly detail?: string;
  readonly status: 'PASS' | 'INFO';
}

export interface GenerationValidationMetric {
  readonly label: string;
  readonly value: string;
  readonly detail?: string;
  readonly status: 'PASS' | 'INFO';
}

export interface GenerationViewModel {
  readonly jobId: string;
  readonly status: GenerationRunStatus;
  readonly seed: number;
  readonly chunkSize: number;
  readonly specificationHash: string;
  readonly updatedAt: string;

  readonly entityCount: number;
  readonly completedEntityCount: number;

  readonly totalTargetRows: number;
  readonly totalGeneratedRows: number;
  readonly progress: number;

  readonly totalChunks: number;
  readonly completedChunks: number;

  readonly elapsedSeconds: number | null;
  readonly rowsPerSecond: number | null;

  readonly entities: readonly EntityGenerationRow[];
  readonly pipeline: readonly GenerationPipelineStage[];

  readonly qualityMetrics: readonly GenerationQualityMetric[];
  readonly validationMetrics: readonly GenerationValidationMetric[];

  readonly lastEntity: EntityGenerationRow | null;
  readonly validationValid: boolean;
  readonly validationErrorCount: number;
}
