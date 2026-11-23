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

export interface GenerationArtifactEvidence {
  path: string;
  size_bytes: number;
  sha256: string;
}

export interface GenerationChunkEvidence {
  chunk_number: number;
  row_start: number;
  row_count: number;
  artifact: GenerationArtifactEvidence;
  committed_at: string;
}

export type GenerationFinalizationStatus =
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'COMMITTED';

export interface GenerationFinalization {
  status: GenerationFinalizationStatus;
  output: GenerationArtifactEvidence | null;
}

export interface GenerationCheckpointEntity {
  target_rows: number;
  chunks: GenerationChunkEvidence[];
  finalization: GenerationFinalization;
}
