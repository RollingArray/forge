import { Injectable } from '@angular/core';

import {
  GenerationArtifacts,
  GenerationPipelineStage,
  GenerationQualityMetric,
  GenerationValidationMetric,
  GenerationViewModel,
  EntityGenerationRow,
} from '../models/generate.models';

@Injectable({
  providedIn: 'root',
})
export class GenerationAdapterService {
  adapt(
    artifacts: GenerationArtifacts,
  ): GenerationViewModel {
    const {
      checkpoint,
      quality,
      validation,
    } = artifacts;

    const entities = Object.entries(
      checkpoint.entities,
    ).map(([entity, checkpointEntity]) =>
      this.adaptEntity(
        entity,
        checkpointEntity,
        checkpoint.chunk_size,
      ),
    );

    const totalTargetRows = entities.reduce(
      (total, entity) =>
        total + entity.plannedRows,
      0,
    );

    const totalGeneratedRows = entities.reduce(
      (total, entity) =>
        total + entity.generatedRows,
      0,
    );

    const completedChunks = entities.reduce(
      (total, entity) =>
        total + entity.completedChunks,
      0,
    );

    const totalChunks = entities.reduce(
      (total, entity) =>
        total + entity.totalChunks,
      0,
    );

    const completedEntityCount =
      entities.filter(
        entity =>
          entity.status === 'COMPLETED',
      ).length;

    const progress =
      totalTargetRows === 0
        ? 0
        : totalGeneratedRows /
          totalTargetRows;

    const generationComplete =
      progress >= 1;

    const validationComplete =
      validation.valid;

    const qualityComplete =
      quality.performance.available;

    const pipeline: readonly GenerationPipelineStage[] = [
      {
        id: 'load-specification',
        label: 'Load Specification',
        status: 'COMPLETED',
      },
      {
        id: 'initialize-plan',
        label: 'Initialize Plan',
        status: entities.length > 0
          ? 'COMPLETED'
          : 'PENDING',
      },
      {
        id: 'generate-data',
        label: 'Generate Data',
        status: generationComplete
          ? 'COMPLETED'
          : 'PENDING',
      },
      {
        id: 'validate',
        label: 'Run Validation',
        status: validationComplete
          ? 'COMPLETED'
          : 'PENDING',
      },
      {
        id: 'quality',
        label: 'Compute Quality',
        status: qualityComplete
          ? 'COMPLETED'
          : 'PENDING',
      },
      {
        id: 'finalize',
        label: 'Finalize',
        status:
          generationComplete &&
          validationComplete &&
          qualityComplete
            ? 'COMPLETED'
            : 'PENDING',
      },
    ];

    const qualityMetrics =
      this.buildQualityMetrics(
        quality,
      );

    const validationMetrics =
      this.buildValidationMetrics(
        validation,
      );

    return {
      jobId: checkpoint.job_id,
      status:
        generationComplete &&
        validationComplete &&
        qualityComplete
          ? 'COMPLETED'
          : generationComplete
            ? 'PARTIAL'
            : 'IN_PROGRESS',

      seed: checkpoint.seed,
      chunkSize: checkpoint.chunk_size,
      specificationHash:
        checkpoint.specification_hash,
      updatedAt: checkpoint.updated_at,

      entityCount: entities.length,
      completedEntityCount,

      totalTargetRows,
      totalGeneratedRows,
      progress,

      totalChunks,
      completedChunks,

      elapsedSeconds:
        quality.performance.available
          ? quality.performance.elapsed_seconds
          : null,

      rowsPerSecond:
        quality.performance.available
          ? quality.performance.rows_per_second
          : null,

      entities,
      pipeline,

      qualityMetrics,
      validationMetrics,

      lastEntity:
        entities.length > 0
          ? entities[entities.length - 1]
          : null,

      validationValid:
        validation.valid,

      validationErrorCount:
        validation.errors.length,
    };
  }

  private adaptEntity(
    entity: string,
    value: {
      readonly completed_chunks: readonly number[];
      readonly target_rows: number;
    },
    chunkSize: number,
  ): EntityGenerationRow {
    const totalChunks =
      Math.ceil(
        value.target_rows /
          chunkSize,
      );

    const completedChunks =
      value.completed_chunks.length;

    const generatedRows =
      Math.min(
        value.target_rows,
        completedChunks *
          chunkSize,
      );

    const progress =
      value.target_rows === 0
        ? 0
        : generatedRows /
          value.target_rows;

    return {
      entity,
      plannedRows: value.target_rows,
      generatedRows,
      progress,
      completedChunks,
      totalChunks,
      status:
        progress >= 1
          ? 'COMPLETED'
          : completedChunks > 0
            ? 'IN_PROGRESS'
            : 'PARTIAL',
    };
  }

  private buildQualityMetrics(
    quality: GenerationArtifacts['quality'],
  ): readonly GenerationQualityMetric[] {
    const population =
      quality.population_fidelity;

    const performance =
      quality.performance;

    return [
      {
        label: 'Population Fidelity',
        value: this.percent(
          population.fidelity_rate,
        ),
        detail:
          `${this.number(population.total_generated_rows)} / ${this.number(population.total_requested_rows)} rows`,
        status:
          population.fidelity_rate >= 1
            ? 'PASS'
            : 'INFO',
      },
      {
        label: 'Distribution Fidelity',
        value:
          `${quality.distribution_fidelity.fields_analyzed}`,
        detail: 'fields analyzed',
        status: 'INFO',
      },
      {
        label: 'Statistical Fidelity',
        value:
          `${quality.statistical_fidelity.numeric_fields_analyzed}`,
        detail: 'numeric fields analyzed',
        status: 'INFO',
      },
      {
        label: 'Identity Space',
        value:
          `${quality.identity_space_utilization.entities_analyzed}`,
        detail: 'entities analyzed',
        status: 'INFO',
      },
      {
        label: 'Relationship Fidelity',
        value:
          `${quality.relationship_fidelity.relationships_analyzed}`,
        detail: 'relationships analyzed',
        status: 'INFO',
      },
      {
        label: 'Performance',
        value:
          performance.available &&
          performance.rows_per_second !== null
            ? `${this.number(Math.round(performance.rows_per_second))}/s`
            : 'Unavailable',
        detail:
          performance.available &&
          performance.elapsed_seconds !== null
            ? `${performance.elapsed_seconds.toFixed(3)} seconds`
            : 'No persisted timing',
        status:
          performance.available
            ? 'PASS'
            : 'INFO',
      },
    ];
  }

  private buildValidationMetrics(
    validation: GenerationArtifacts['validation'],
  ): readonly GenerationValidationMetric[] {
    const root =
      validation.validation;

    const schema =
      this.objectAt(root, 'schema');

    const primaryKeys =
      this.objectAt(
        root,
        'primary_keys',
      );

    const completeness =
      this.objectAt(
        root,
        'completeness',
      );

    return [
      {
        label: 'Validation',
        value:
          validation.valid
            ? 'Valid'
            : 'Invalid',
        detail:
          validation.errors.length === 0
            ? 'No validation errors'
            : `${validation.errors.length} error(s)`,
        status:
          validation.valid
            ? 'PASS'
            : 'INFO',
      },
      {
        label: 'Schema',
        value:
          this.ratio(
            this.numberAt(
              schema,
              'entities_schema_valid',
            ),
            this.numberAt(
              schema,
              'entities_checked',
            ),
          ),
        detail: 'entities valid',
        status: 'PASS',
      },
      {
        label: 'Primary Keys',
        value:
          this.numberAt(
            primaryKeys,
            'duplicate_count',
          ).toLocaleString(),
        detail: 'duplicate identities',
        status:
          this.numberAt(
            primaryKeys,
            'duplicate_count',
          ) === 0
            ? 'PASS'
            : 'INFO',
      },
      {
        label: 'Completeness',
        value:
          this.numberAt(
            completeness,
            'missing_value_count',
          ).toLocaleString(),
        detail: 'missing values',
        status:
          this.numberAt(
            completeness,
            'missing_value_count',
          ) === 0
            ? 'PASS'
            : 'INFO',
      },
    ];
  }

  private objectAt(
    value: Record<string, unknown>,
    key: string,
  ): Record<string, unknown> {
    const result = value[key];

    return result &&
      typeof result === 'object' &&
      !Array.isArray(result)
      ? result as Record<string, unknown>
      : {};
  }

  private numberAt(
    value: Record<string, unknown>,
    key: string,
  ): number {
    const result = value[key];

    return typeof result === 'number'
      ? result
      : 0;
  }

  private ratio(
    numerator: number,
    denominator: number,
  ): string {
    return denominator > 0
      ? `${numerator} / ${denominator}`
      : 'Unavailable';
  }

  private percent(value: number): string {
    return `${(value * 100).toFixed(value >= 0.995 ? 0 : 1)}%`;
  }

  private number(value: number): string {
    return value.toLocaleString();
  }
}
