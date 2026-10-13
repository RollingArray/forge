import { Injectable } from '@angular/core';
import { GenerationReadiness, GenerationJobResponse } from '../models/generation.models';
import { GenerationPipelineNode } from '../../../core/interfaces/generation-pipeline-node.interface';
import { GenerationPipelineGraph } from '../../../core/interfaces/generation-pipeline-graph.interface';
import { GenerationPipelineEdge } from '../../../core/interfaces/generation-pipeline-edge.interface';

@Injectable({
  providedIn: 'root',
})
export class GenerationPipelineMapper {
  fromReadiness(
    readiness: GenerationReadiness | null,
    job: GenerationJobResponse | null,
  ): GenerationPipelineNode[] {
    if (!readiness) {
      return [];
    }

    return readiness.entities.map((entity) => {
      const runtimeEntity = job?.entities.find((item) => item.entity_name === entity.entity_name);

      const generatedRows = runtimeEntity?.generated_rows ?? 0;

      const progress = entity.target_rows > 0 ? generatedRows / entity.target_rows : 0;

      return {
        id: entity.entity_name,
        entityName: entity.entity_name,
        targetRows: entity.target_rows,
        generatedRows,
        dependencies: entity.dependencies,
        status: runtimeEntity?.status ?? 'NOT_STARTED',
        progress,
      };
    });
  }

  toGraph(nodes: GenerationPipelineNode[]): GenerationPipelineGraph {
    const edges: GenerationPipelineEdge[] = [];

    for (const node of nodes) {
      for (const dependency of node.dependencies) {
        edges.push({
          source: dependency,
          target: node.id,
        });
      }
    }

    return {
      nodes,
      edges,
    };
  }
}
