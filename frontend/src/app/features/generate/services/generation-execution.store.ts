import { Injectable, inject, signal } from '@angular/core';

import {
  GenerationActivityEvent,
  GenerationEntityCompletedEvent,
  GenerationJobResponse,
  GenerationSseEvent,
} from '../models/generation.models';

import { GenerationService } from './generation.service';
import { GenerationCheckpoint } from '../../../shared/models/generation-checkpoint.models';
import { Subscription } from 'rxjs';


@Injectable({
  providedIn: 'root',
})
export class GenerationExecutionStore {

  private readonly generationService = inject(GenerationService);

  private executionSubscription: Subscription | null = null;

  readonly generationJob = signal<GenerationJobResponse | null>(null);
  readonly generationCheckpoint = signal<GenerationCheckpoint | null>(null);

  readonly lastEvent = signal<GenerationSseEvent | null>(null);

  readonly generationActivities = signal<GenerationActivityEvent[]>([]);
  readonly isGenerating = signal(false);

  readonly activeSemanticCall = signal<
    Extract<
      GenerationSseEvent,
      { type: 'SEMANTIC_CALL_STARTED' }
    >['data'] | null
  >(null);


  setJob(
    job: GenerationJobResponse,
  ): void {
    this.generationJob.set(job);
  }

  connect(
    dataModelId: string,
    jobId: string,
  ): void {

    this.executionSubscription?.unsubscribe();

    this.executionSubscription = this.generationService
      .connectToGenerationEvents(
        dataModelId,
        jobId,
      )
      .subscribe({
        next: (event) => {
          this.handleEvent(event);
        },
      });
  }



  handleEvent(
    event: GenerationSseEvent,
  ): void {
    console.log('GENERATION EVENT', event);

    this.lastEvent.set(event);

    switch (event.type) {

      case 'JOB_SNAPSHOT':
        this.generationJob.set(event.data);
        this.isGenerating.set(
          event.data.status === 'QUEUED' || event.data.status === 'RUNNING',
        );
        break;

      case 'GENERATION_ACTIVITY':
        this.isGenerating.set(true);
        this.appendGenerationActivity(event.data);
        break;

      case 'SEMANTIC_CALL_STARTED':
        this.activeSemanticCall.set(event.data);
        break;

      case 'CHUNK_COMMITTED':
        this.activeSemanticCall.set(null);
        this.applyChunkProgress(event.data);
        this.applyCheckpointChunk(event.data);
        break;


      case 'ENTITY_COMPLETED':
        this.applyEntityCompleted(event.data);
        break;


      case 'GENERATION_COMPLETED':
        this.isGenerating.set(false);
        this.activeSemanticCall.set(null);
        this.applyGenerationCompleted(event.data);
        break;
    }
  }


  private appendGenerationActivity(
    activity: GenerationActivityEvent,
  ): void {
    this.generationActivities.update((activities) => [
      ...activities,
      activity,
    ]);
  }

  private applyCheckpointChunk(
    event: Extract<
      GenerationSseEvent,
      { type: 'CHUNK_COMMITTED' }
    >['data'],
  ): void {
    this.generationCheckpoint.update((checkpoint) => {
      if (!checkpoint) {
        return checkpoint;
      }

      const existing = checkpoint.entities[event.entity_name] ?? {
        target_rows: event.entity_target_rows,
        completed_chunks: [],
      };

      const completedChunks = existing.completed_chunks.includes(
        event.chunk_number,
      )
        ? existing.completed_chunks
        : [...existing.completed_chunks, event.chunk_number].sort(
            (a, b) => a - b,
          );

      return {
        ...checkpoint,
        updated_at: event.checkpoint_updated_at,
        entities: {
          ...checkpoint.entities,
          [event.entity_name]: {
            ...existing,
            target_rows: event.entity_target_rows,
            completed_chunks: completedChunks,
          },
        },
      };
    });
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
      entities: current.entities.map(entity =>
        entity.entity_name === event.entity_name
          ? {
              ...entity,
              generated_rows: event.entity_generated_rows,
              completed_chunks: event.chunk_number,
              total_chunks: event.total_chunks,
              status: 'RUNNING',
            }
          : entity,
      ),
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
              elapsed_seconds: event.elapsed_seconds,
              throughput_rows_per_second:
                event.throughput_rows_per_second,
              peak_memory_mb: event.peak_memory_mb,
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
      elapsed_seconds: event.elapsed_seconds,
      throughput_rows_per_second: event.throughput_rows_per_second,
      peak_memory_mb: event.peak_memory_mb,
      progress: event.progress,
    });
  }
}
