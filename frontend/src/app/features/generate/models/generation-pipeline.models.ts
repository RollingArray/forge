import { GenerationEntityStatus } from './generation.models';

export interface GenerationPipelineNode {
  id: string;
  entityName: string;
  targetRows: number;
  generatedRows: number;
  dependencies: string[];
  status: GenerationEntityStatus | 'NOT_STARTED';
  progress: number;
}

export interface GenerationPipelineEdge {
  source: string;
  target: string;
}


export interface GenerationPipelineGraph {
  nodes: GenerationPipelineNode[];
  edges: GenerationPipelineEdge[];
}
