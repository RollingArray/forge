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
  progress: number;
}

export interface GenerationEntityCompletedEvent {
  entity_name: string;
  target_rows: number;
  generated_rows: number;
  status: 'COMPLETED';
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
      type: 'ENTITY_COMPLETED';
      data: GenerationEntityCompletedEvent;
    }
  | {
      type: 'GENERATION_COMPLETED';
      data: GenerationCompletedEvent;
    };
