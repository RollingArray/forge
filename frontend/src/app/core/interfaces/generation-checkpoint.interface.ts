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
  schema_version: number;
  job_id: string;
  specification_hash: string;
  seed: number;
  chunk_size: number;
  entities: Record<string, GenerationCheckpointEntity>;
  updated_at: string;
}
