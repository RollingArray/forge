
export interface GenerationEntityReadiness {
  entity_name: string;
  target_rows: number;
  generation_order: number;
  dependencies: string[];
}

export interface GenerationReadiness {
  data_model_id: string;
  ready: boolean;
  entity_count: number;
  total_target_rows: number;
  generation_order: string[];
  entities: GenerationEntityReadiness[];
  warnings: string[];
  errors: string[];
  generation: Record<string, unknown>;
}


export type GenerationJobStatus =
  | 'CREATED'
  | 'PLANNING'
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type GenerationEntityStatus =
  | 'NOT_STARTED'
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface GenerationEntityProgress {
  entity_name: string;
  target_rows: number;
  generated_rows: number;
  chunk_size: number;
  completed_chunks: number;
  total_chunks: number;
  status: GenerationEntityStatus;

  // Runtime telemetry returned by the generation backend.
  throughput_rows_per_second?: number | null;
  elapsed_seconds?: number | null;
  peak_memory_mb?: number | null;
}

export interface GenerationJobResponse {
  data_model_id: string;
  job_id: string;
  status: GenerationJobStatus;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  total_target_rows: number;
  total_generated_rows: number;
  progress: number;
  entities: GenerationEntityProgress[];
  error: string | null;
  throughput_rows_per_second: number | null;
}

export interface GenerationChunkCommittedEvent {
  entity_name: string;
  chunk_number: number;
  total_chunks: number;
  generated_rows: number;
  entity_generated_rows: number;
  entity_target_rows: number;
  entity_progress: number;
  progress: number;
}

export interface GenerationEntityCompletedEvent {
  entity_name: string;
  target_rows: number;
  generated_rows: number;
  status: 'COMPLETED';
  elapsed_seconds: number | null;
  throughput_rows_per_second: number | null;
  peak_memory_mb: number | null;
  progress: number;
}

export interface GenerationCompletedEvent {
  job_id: string;
  status: GenerationJobStatus;
  generated_rows: number;
  expected_rows: number;
  valid: boolean;
  error_count: number;
  progress: number;
}

export interface GenerationActivityEvent {
  sequence: number;
  timestamp: string;
  entity_name?: string;
  stage: string;
  status: string;
  field_name?: string;
  chunk_number?: number;
  call_number?: number;
  requested_count?: number;
  generated_rows?: number;
  elapsed_seconds?: number;
  throughput_rows_per_second?: number;
  peak_memory_mb?: number;
}

export interface GenerationSemanticCallStartedEvent {
  entity_name: string;
  field_name: string;
  chunk_number: number;
  call_number: number;
  requested_count: number;
}

export type GenerationSseEvent =
  | {
      type: 'JOB_SNAPSHOT';
      data: GenerationJobResponse;
    }
  | {
      type: 'CHUNK_COMMITTED';
      data: GenerationChunkCommittedEvent;
    }
  | {
      type: 'SEMANTIC_CALL_STARTED';
      data: GenerationSemanticCallStartedEvent;
    }
  | {
      type: 'GENERATION_ACTIVITY';
      data: GenerationActivityEvent;
    }
  | {
      type: 'ENTITY_COMPLETED';
      data: GenerationEntityCompletedEvent;
    }
  | {
      type: 'GENERATION_COMPLETED';
      data: GenerationCompletedEvent;
    };
