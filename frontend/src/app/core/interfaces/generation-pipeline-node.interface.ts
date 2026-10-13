/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: generation-pipeline-node.interface.ts
 * Purpose: Defines the generation pipeline node contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { GenerationEntityStatus } from '../../features/generate/models/generation.models';

export interface GenerationPipelineNode {
  id: string;
  entityName: string;
  targetRows: number;
  generatedRows: number;
  dependencies: string[];
  status: GenerationEntityStatus | 'NOT_STARTED';
  progress: number;
}
