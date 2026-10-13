/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: generation-pipeline-graph.interface.ts
 * Purpose: Defines the generation pipeline graph contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import type { GenerationPipelineNode } from './generation-pipeline-node.interface';
import type { GenerationPipelineEdge } from './generation-pipeline-edge.interface';

export interface GenerationPipelineGraph {
  nodes: GenerationPipelineNode[];
  edges: GenerationPipelineEdge[];
}
