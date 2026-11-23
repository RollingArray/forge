/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: generation-checkpoint.interface.ts
 * Purpose: Defines the generation checkpoint contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import type { GenerationCheckpointEntity } from './generation-checkpoint-entity.interface';

export interface GenerationCheckpoint {
  schema_version: 2;
  data_model_id: string;
  job_id: string;
  specification_hash: string;
  seed: number;
  chunk_size: number;
  algorithm_version: string;
  attempt_id: string;
  entities: Record<string, GenerationCheckpointEntity>;
  created_at: string;
  updated_at: string;
}


/**
 * Lightweight, event-driven checkpoint progress for the live UI.
 * This projection is not recovery evidence and must not replace
 * the durable GenerationCheckpointManifest.
 */
export interface GenerationCheckpointLiveEntityProgress {
  saved_chunks: number;
  target_rows: number;
  generated_rows: number;
}

export interface GenerationCheckpointLiveProgress {
  job_id: string;
  updated_at: string;
  entities: Record<string, GenerationCheckpointLiveEntityProgress>;
}
