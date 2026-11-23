import { Injectable, inject, signal } from '@angular/core';
import {
  GenerationActivityEvent,
  GenerationEntityCompletedEvent,
  GenerationJobResponse,
  GenerationSseEvent,
} from '../models/generation.models';
import { GenerationService } from './generation.service';
import {
  GenerationCheckpoint,
  GenerationCheckpointLiveProgress,
} from '../../../core/interfaces/generation-checkpoint.interface';
import { Subscription } from 'rxjs';



@Injectable({
  providedIn: 'root',
})
export class GenerationExecutionStore {

  private readonly generationService = inject(GenerationService);

  private executionSubscription: Subscription | null = null;



  readonly generationJob = signal<GenerationJobResponse | null>(null);
  readonly generationCheckpoint = signal<GenerationCheckpoint | null>(null);
  readonly generationCheckpointLiveProgress =
    signal<GenerationCheckpointLiveProgress | null>(null);

  readonly lastEvent = signal<GenerationSseEvent | null>(null);

  readonly generationActivities = signal<GenerationActivityEvent[]>([]);
  readonly isGenerating = signal(false);
  readonly sseConnectionError = signal<string | null>(null);

  readonly activeSemanticCall = signal<
    Extract<
      GenerationSseEvent,
      { type: 'SEMANTIC_CALL_STARTED' }
    >['data'] | null
  >(null);


  setCheckpoint(checkpoint: GenerationCheckpoint): void {
    const current = this.generationCheckpoint();

    if (current?.job_id === checkpoint.job_id) {
      const currentTimestamp = Date.parse(current.updated_at);
      const incomingTimestamp = Date.parse(checkpoint.updated_at);

      if (
        Number.isFinite(currentTimestamp) &&
        Number.isFinite(incomingTimestamp) &&
        incomingTimestamp < currentTimestamp
      ) {
        return;
      }
    }

    this.generationCheckpoint.set(checkpoint);

    const live = this.generationCheckpointLiveProgress();

    if (live?.job_id === checkpoint.job_id) {
      const liveTimestamp = Date.parse(live.updated_at);
      const incomingTimestamp = Date.parse(checkpoint.updated_at);

      if (
        Number.isFinite(liveTimestamp) &&
        Number.isFinite(incomingTimestamp) &&
        liveTimestamp > incomingTimestamp
      ) {
        return;
      }
    }

    this.generationCheckpointLiveProgress.set({
      job_id: checkpoint.job_id,
      updated_at: checkpoint.updated_at,
      entities: Object.fromEntries(
        Object.entries(checkpoint.entities).map(([entityName, entity]) => [
          entityName,
          {
            saved_chunks: entity.chunks.length,
            target_rows: entity.target_rows,
            generated_rows: entity.chunks.reduce(
              (total, chunk) => total + chunk.row_count,
              0,
            ),
          },
        ]),
      ),
    });
  }

  private applyLiveCheckpointChunk(
    event: Extract<
      GenerationSseEvent,
      { type: 'CHUNK_COMMITTED' }
    >['data'],
  ): void {
    const job = this.generationJob();

    if (!job) {
      return;
    }

    const current = this.generationCheckpointLiveProgress();
    const entities = current?.job_id === job.job_id
      ? current.entities
      : {};

    const previous = entities[event.entity_name];

    this.generationCheckpointLiveProgress.set({
      job_id: job.job_id,
      updated_at: event.checkpoint_updated_at,
      entities: {
        ...entities,
        [event.entity_name]: {
          saved_chunks: Math.max(
            previous?.saved_chunks ?? 0,
            event.chunk_number,
          ),
          target_rows: event.entity_target_rows,
          generated_rows: event.entity_generated_rows,
        },
      },
    });
  }

  private applyLiveEntityCompletion(
    event: GenerationEntityCompletedEvent,
  ): void {
    const job = this.generationJob();

    if (!job) {
      return;
    }

    const current = this.generationCheckpointLiveProgress();
    const entities = current?.job_id === job.job_id
      ? current.entities
      : {};

    const previous = entities[event.entity_name];

    this.generationCheckpointLiveProgress.set({
      job_id: job.job_id,
      updated_at: current?.job_id === job.job_id
        ? current.updated_at
        : new Date().toISOString(),
      entities: {
        ...entities,
        [event.entity_name]: {
          saved_chunks: previous?.saved_chunks ?? 0,
          target_rows: event.target_rows,
          generated_rows: event.generated_rows,
        },
      },
    });
  }

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
    this.sseConnectionError.set(null);

    this.executionSubscription = this.generationService
      .connectToGenerationEvents(
        dataModelId,
        jobId,
      )
      .subscribe({
        next: (event) => {
          this.sseConnectionError.set(null);
          this.handleEvent(event);
        },
        error: (error: unknown) => {
          this.executionSubscription = null;
          this.sseConnectionError.set(
            error instanceof Error
              ? error.message
              : 'Live generation updates could not be received. The job may still be running.',
          );
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
          event.data.status === 'PREPARING' ||
          event.data.status === 'QUEUED' ||
          event.data.status === 'RUNNING',
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
        this.applyLiveCheckpointChunk(event.data);
        break;


      case 'ENTITY_COMPLETED':
        this.applyEntityCompleted(event.data);
        this.applyLiveEntityCompletion(event.data);
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
