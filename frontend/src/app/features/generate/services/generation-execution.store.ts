import { Injectable, signal } from '@angular/core';

import {
  GenerationEntityCompletedEvent,
  GenerationJobResponse,
  GenerationSseEvent,
} from '../models/generation.models';


@Injectable({
  providedIn: 'root',
})
export class GenerationExecutionStore {

  readonly generationJob = signal<GenerationJobResponse | null>(null);

  readonly lastEvent = signal<GenerationSseEvent | null>(null);


  setJob(
    job: GenerationJobResponse,
  ): void {
    this.generationJob.set(job);
  }


  handleEvent(
    event: GenerationSseEvent,
  ): void {
    this.lastEvent.set(event);

    switch (event.type) {

      case 'JOB_SNAPSHOT':
        this.generationJob.set(event.data);
        break;


      case 'CHUNK_COMMITTED':
        this.applyChunkProgress(event.data);
        break;


      case 'ENTITY_COMPLETED':
        this.applyEntityCompleted(event.data);
        break;


      case 'GENERATION_COMPLETED':
        this.applyGenerationCompleted(event.data);
        break;
    }
  }


  private applyChunkProgress(
    event: Extract<
      GenerationSseEvent,
      { type: 'CHUNK_COMMITTED' }
    >['data'],
  ): void {

    const current = this.generationJob();

    if (!current) {
      return;
    }

    this.generationJob.set({
      ...current,
      total_generated_rows: event.generated_rows,
      progress: event.progress,
    });
  }


  private applyEntityCompleted(
    event: GenerationEntityCompletedEvent,
  ): void {

    const current = this.generationJob();

    if (!current) {
      return;
    }

    this.generationJob.set({
      ...current,
      progress: event.progress,
      entities: current.entities.map(entity =>
        entity.entity_name === event.entity_name
          ? {
              ...entity,
              target_rows: event.target_rows,
              generated_rows: event.generated_rows,
              status: event.status,
            }
          : entity,
      ),
    });
  }


  private applyGenerationCompleted(
    event: Extract<
      GenerationSseEvent,
      { type: 'GENERATION_COMPLETED' }
    >['data'],
  ): void {

    const current = this.generationJob();

    if (!current) {
      return;
    }

    this.generationJob.set({
      ...current,
      status: event.status,
      total_generated_rows: event.generated_rows,
      progress: event.progress,
    });
  }
}
