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
import { environment } from '../../../../environments/environment';



@Injectable({
  providedIn: 'root',
})
export class GenerationExecutionStore {

  private readonly generationService = inject(GenerationService);

  private executionSubscription: Subscription | null = null;

  private activeDataModelId: string | null = null;
  private activeJobId: string | null = null;
  private contextRevision = 0;

  /**
   * Start a clean in-memory execution context.
   * This never cancels or deletes the persisted backend job.
   */
  beginNewExecution(dataModelId: string): number {
    this.activateContext(dataModelId, null);
    return this.contextRevision;
  }

  /**
   * Establish ownership of one specific persisted generation job.
   */
  restoreExecution(dataModelId: string, jobId: string): number {
    this.activateContext(dataModelId, jobId);
    return this.contextRevision;
  }

  /**
   * Current revision token for guarding asynchronous responses.
   */
  getContextRevision(): number {
    return this.contextRevision;
  }

  /**
   * Check whether an asynchronous operation still belongs to
   * the currently active execution context.
   */
  isCurrentContext(
    dataModelId: string,
    jobId: string | null,
    revision: number,
  ): boolean {
    return (
      revision === this.contextRevision &&
      dataModelId === this.activeDataModelId &&
      (jobId === null || jobId === this.activeJobId)
    );
  }

  /**
   * Disconnect live UI updates without affecting backend execution.
   */
  disconnect(): void {
    this.executionSubscription?.unsubscribe();
    this.executionSubscription = null;
  }

  private activateContext(
    dataModelId: string,
    jobId: string | null,
  ): void {
    this.disconnect();

    this.contextRevision += 1;
    this.activeDataModelId = dataModelId;
    this.activeJobId = jobId;

    this.generationJob.set(null);
    this.generationCheckpoint.set(null);
    this.generationCheckpointLiveProgress.set(null);
    this.lastEvent.set(null);
    this.generationActivities.set([]);
    this.isGenerating.set(false);
    this.sseConnectionError.set(null);
    this.activeSemanticCall.set(null);
  }

  private ensureJobContext(job: GenerationJobResponse): void {
    if (
      this.activeDataModelId !== job.data_model_id ||
      (this.activeJobId !== null && this.activeJobId !== job.job_id)
    ) {
      this.activateContext(job.data_model_id, job.job_id);
      return;
    }

    if (this.activeJobId === null) {
      this.activeJobId = job.job_id;
    }
  }



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


  setCheckpoint(
    checkpoint: GenerationCheckpoint,
    expectedRevision: number = this.contextRevision,
  ): void {
    if (
      expectedRevision !== this.contextRevision ||
      checkpoint.job_id !== this.activeJobId ||
      this.activeDataModelId === null
    ) {
      return;
    }
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
    expectedRevision: number = this.contextRevision,
  ): void {
    if (
      expectedRevision !== this.contextRevision ||
      !job.data_model_id
    ) {
      return;
    }

    this.ensureJobContext(job);
    this.generationJob.set(job);
  }

  connect(
    dataModelId: string,
    jobId: string,
  ): void {
    if (
      dataModelId !== this.activeDataModelId ||
      jobId !== this.activeJobId
    ) {
      return;
    }

    this.disconnect();
    const subscriptionRevision = this.contextRevision;
    this.sseConnectionError.set(null);

    this.executionSubscription = this.generationService
      .connectToGenerationEvents(
        dataModelId,
        jobId,
      )
      .subscribe({
        next: (event) => {
          if (subscriptionRevision !== this.contextRevision) {
            return;
          }

          this.sseConnectionError.set(null);
          this.handleEvent(event, subscriptionRevision);
        },
        error: (error: unknown) => {
          if (subscriptionRevision !== this.contextRevision) {
            return;
          }

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
    expectedRevision: number = this.contextRevision,
  ): void {
    if (
      expectedRevision !== this.contextRevision ||
      this.activeDataModelId === null ||
      this.activeJobId === null
    ) {
      return;
    }

    let beforeSavedChunks = 0;
    let beforeGeneratedRows = 0;

    if (environment.sseDiagnostics) {
      if (event.type === 'CHUNK_COMMITTED') {
        const checkpointBefore = this.generationCheckpointLiveProgress();
        const beforeEntity = checkpointBefore?.entities[event.data.entity_name];
        beforeSavedChunks = beforeEntity?.saved_chunks ?? 0;
        beforeGeneratedRows = beforeEntity?.generated_rows ?? 0;
      }

      const uiHandler: Record<GenerationSseEvent['type'], string> = {
        JOB_SNAPSHOT: 'generationJob / isGenerating',
        GENERATION_STARTED: 'generationJob / isGenerating',
        GENERATION_ACTIVITY: 'generationActivities',
        SEMANTIC_CALL_STARTED: 'activeSemanticCall',
        CHUNK_COMMITTED: 'applyChunkProgress / live checkpoint projection',
        ENTITY_COMPLETED: 'applyEntityCompleted / live entity completion',
        GENERATION_COMPLETED: 'applyGenerationCompleted / terminal job state',
        GENERATION_PAUSED: 'applyGenerationControl / paused job state',
        GENERATION_CANCELLED: 'applyGenerationControl / cancelled job state',
      };

      const data = event.data as unknown as Record<string, unknown>;
      console.info('[FORGE SSE][RECEIVED]', {
        timestamp: new Date().toISOString(),
        eventType: event.type,
        purpose: event.type === 'GENERATION_ACTIVITY'
          ? `${String(data['stage'] ?? 'UNKNOWN')}:${String(data['status'] ?? 'UNKNOWN')}`
          : event.type,
        uiHandler: uiHandler[event.type],
        jobId: this.generationJob()?.job_id ?? data['job_id'] ?? null,
        entity: data['entity_name'] ?? null,
        field: data['field_name'] ?? null,
        stage: data['stage'] ?? null,
        status: data['status'] ?? null,
        chunk: data['chunk_number'] ?? null,
      });
    }

    this.lastEvent.set(event);

    switch (event.type) {

      case 'JOB_SNAPSHOT':
      case 'GENERATION_STARTED':
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


      case 'GENERATION_PAUSED':
      case 'GENERATION_CANCELLED': {
        const current = this.generationJob();

        this.isGenerating.set(false);
        this.activeSemanticCall.set(null);

        if (current) {
          this.generationJob.set({
            ...current,
            status: event.data.status,
            total_generated_rows: event.data.generated_rows,
            progress: event.data.progress,
          });
        }

        break;
      }

      case 'GENERATION_COMPLETED':
        this.isGenerating.set(false);
        this.activeSemanticCall.set(null);
        this.applyGenerationCompleted(event.data);
        break;
    }

    if (environment.sseDiagnostics && event.type === 'CHUNK_COMMITTED') {
      const checkpointAfter = this.generationCheckpointLiveProgress();
      const afterEntity = checkpointAfter?.entities[event.data.entity_name];

      console.info('[FORGE SSE][UI UPDATE]', {
        timestamp: new Date().toISOString(),
        eventType: event.type,
        entity: event.data.entity_name,
        savedBatches: {
          before: beforeSavedChunks,
          after: afterEntity?.saved_chunks ?? 0,
        },
        generatedRows: {
          before: beforeGeneratedRows,
          after: afterEntity?.generated_rows ?? 0,
        },
        targetRows: afterEntity?.target_rows ?? event.data.entity_target_rows,
        projectionUpdated: Boolean(afterEntity),
      });
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
