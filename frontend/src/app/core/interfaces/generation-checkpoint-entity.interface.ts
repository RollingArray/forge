/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: generation-checkpoint-entity.interface.ts
 * Purpose: Defines the generation checkpoint entity contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface GenerationCheckpointEntity {
  target_rows: number;
  completed_chunks: number[];
}
