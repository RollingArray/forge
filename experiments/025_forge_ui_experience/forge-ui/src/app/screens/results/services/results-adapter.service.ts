import { Injectable } from '@angular/core';

import {
  ResultsCheckpoint,
  ResultsQuality,
  ResultsValidation,
  ResultsViewModel,
} from '../models/results.models';

@Injectable({
  providedIn: 'root',
})
export class ResultsAdapterService {
  adapt(
    checkpoint: ResultsCheckpoint,
    quality: ResultsQuality,
    validation: ResultsValidation,
  ): ResultsViewModel {
    const entities = Object.values(
      checkpoint.entities,
    )
      .map((entity, index) => {
        const recordsGenerated = Math.min(
          entity.target_rows,
          entity.completed_chunks *
            checkpoint.chunk_size,
        );

        return {
          index: index + 1,
          name: entity.entity,
          targetRows: entity.target_rows,
          recordsGenerated,
          outputFile:
            `${entity.entity}_synthetic.csv`,
        };
      })
      .sort(
        (a, b) =>
          a.index - b.index,
      );

    const totalRecords =
      quality.performance.total_generated_rows;

    const allEntitiesCompleted =
      entities.every(
        entity =>
          entity.recordsGenerated >=
          entity.targetRows,
      );

    return {
      status:
        allEntitiesCompleted &&
        validation.valid
          ? 'COMPLETED'
          : 'INCOMPLETE',

      jobId:
        checkpoint.job_id,

      updatedAt:
        checkpoint.updated_at,

      entities,

      totalEntities:
        entities.length,

      totalRecords,

      qualityReportAvailable:
        true,

      validationReportAvailable:
        true,

      generatedEntityFiles:
        entities.length,
    };
  }
}
