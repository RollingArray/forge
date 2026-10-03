export interface GenerationCheckpointEntity {
  target_rows: number;
  completed_chunks: number[];
}

export interface GenerationCheckpoint {
  schema_version: number;
  job_id: string;
  specification_hash: string;
  seed: number;
  chunk_size: number;
  entities: Record<string, GenerationCheckpointEntity>;
  updated_at: string;
}
