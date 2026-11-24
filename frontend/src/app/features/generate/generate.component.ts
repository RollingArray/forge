import { formatStatusLabel } from '../../shared/utils/status-label.util';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import { WorkflowRowComponent } from '../../shared/components/workflow-row/workflow-row.component';
import {
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';
import { GenerationService } from './services/generation.service';
import { GenerationCheckpoint } from '../../core/interfaces/generation-checkpoint.interface';
import { GenerationExecutionStore } from './services/generation-execution.store';
import { GenerationPipelineMapper } from './services/generation-pipeline.mapper';
import { MetricGridComponent } from '../../shared/components/metric-grid/metric-grid.component';
import { WorkspaceHeaderComponent } from '../../shared/components/workspace-header/workspace-header.component';
import { StatusCardComponent } from '../../shared/components/status-card/status-card.component';
import { WorkspaceSectionComponent } from '../../shared/components/workspace-section/workspace-section.component';
import { MetricCardData } from '../../shared/components/metric-grid/metric-card-data';
import { GenerationPipelineComponent } from './components/generation-pipeline/generation-pipeline.component';
import { EntityGenerationProgressComponent } from './components/entity-generation-progress/entity-generation-progress.component';
import { GenerationCheckpointComponent } from './components/generation-checkpoint/generation-checkpoint.component';
import { GenerationActivityComponent } from '../../shared/components/generation-activity/generation-activity.component';
import {
  GenerationJobResponse,
  GenerationReadiness,
} from './models/generation.models';


@Component({
  selector: 'app-generate',
  standalone: true,
  imports: [
    CommonModule,
    WorkflowPageComponent,
    WorkflowRowComponent,
    MetricGridComponent,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    GenerationPipelineComponent,
    EntityGenerationProgressComponent,
    GenerationCheckpointComponent,
    GenerationActivityComponent,
    StatusCardComponent,
  ],
  templateUrl: './generate.component.html',
  styleUrl: './generate.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerateComponent {
  readonly formatStatusLabel = formatStatusLabel;

  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly generationService = inject(GenerationService);
  private readonly executionStore = inject(GenerationExecutionStore);
  private readonly pipelineMapper = inject(GenerationPipelineMapper);

  dataModelId = '';
  jobId = '';

  readonly steps: readonly WorkflowStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];

  readonly activeStep: WorkflowStep = 'generate';

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.executionStore.disconnect();
    });

    this.route.paramMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        this.handleRouteParameters(
          params.get('dataModelId') ?? '',
          params.get('jobId') ?? '',
        );
      });
  }

  private handleRouteParameters(
    dataModelId: string,
    jobId: string,
  ): void {
    this.dataModelId = dataModelId;
    this.jobId = jobId;

    // Reset component-local state for every route context.
    this.generationReadiness.set(null);
    this.generationLoading.set(true);
    this.generationError.set(null);
    this.generationCheckpointLoading.set(false);
    this.generationCheckpointError.set(null);
    this.generationActionLoading.set(false);

    if (!dataModelId) {
      this.executionStore.disconnect();
      this.generationLoading.set(false);
      this.generationError.set('Data model could not be identified.');
      return;
    }

    // A route without a job ID is always a fresh execution intent.
    // A route with a job ID restores only that persisted job.
    const revision = jobId
      ? this.executionStore.restoreExecution(dataModelId, jobId)
      : this.executionStore.beginNewExecution(dataModelId);

    this.loadGenerationReadiness(dataModelId, revision);

    if (jobId) {
      this.loadExistingGenerationJob(dataModelId, jobId, revision);
    }
  }

  private loadExistingGenerationJob(
    dataModelId: string,
    jobId: string,
    revision: number,
  ): void {
    if (!dataModelId || !jobId) {
      return;
    }

    this.generationService
      .getGenerationJob(dataModelId, jobId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (job) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              jobId,
              revision,
            )
          ) {
            return;
          }

          if (
            job.data_model_id !== dataModelId ||
            job.job_id !== jobId
          ) {
            this.generationError.set(
              'The backend returned a different generation job than the one requested.',
            );
            return;
          }

          this.executionStore.setJob(job, revision);

          if (
            job.status === 'PREPARING' ||
            job.status === 'QUEUED' ||
            job.status === 'RUNNING'
          ) {
            this.executionStore.connect(dataModelId, job.job_id);
          }

          this.loadGenerationCheckpoint(dataModelId, job.job_id, revision);
        },
        error: (error) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              jobId,
              revision,
            )
          ) {
            return;
          }

          this.generationError.set(
            error?.error?.detail ??
              error?.message ??
              'Generation job could not be loaded.',
          );
        },
      });
  }

  private loadGenerationReadiness(
    dataModelId: string,
    revision: number,
  ): void {
    if (!dataModelId) {
      this.generationLoading.set(false);
      this.generationError.set('Data model could not be identified.');
      return;
    }

    this.generationService
      .getGenerationReadiness(dataModelId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (readiness) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              null,
              revision,
            )
          ) {
            return;
          }

          this.generationReadiness.set(readiness);
          this.generationLoading.set(false);
        },
        error: () => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              null,
              revision,
            )
          ) {
            return;
          }

          this.generationLoading.set(false);
          this.generationError.set(
            'Generation readiness could not be loaded.',
          );
        },
      });
  }

  readonly generationReadiness = signal<GenerationReadiness | null>(null);
  readonly generationLoading = signal(true);
  readonly generationError = signal<string | null>(null);
  readonly generationJob = this.executionStore.generationJob;
  readonly activeSemanticCall = this.executionStore.activeSemanticCall;
  readonly generationActivities = this.executionStore.generationActivities;
  readonly isGenerating = this.executionStore.isGenerating;
  readonly sseConnectionError = this.executionStore.sseConnectionError;
  readonly generationCheckpoint = this.executionStore.generationCheckpoint;
  readonly generationCheckpointLiveProgress = this.executionStore.generationCheckpointLiveProgress;
  readonly generationCheckpointLoading = signal(false);
  readonly generationCheckpointError = signal<string | null>(null);
  readonly generationActionLoading = signal(false);

  readonly pipelineNodes = computed(() =>
    this.pipelineMapper.fromReadiness(
      this.generationReadiness(),
      this.generationJob(),
    ),
  );

  readonly pipelineGraph = computed(() =>
    this.pipelineMapper.toGraph(
      this.pipelineNodes(),
    ),
  );
  readonly generationJobIdDisplay = computed(
    () => this.generationJob()?.job_id ?? '—',
  );

  readonly generationJobDetail = computed(
    () =>
      this.generationJob() !== null
        ? 'Generation job created'
        : 'Assigned when generation starts',
  );

  readonly generationTargetRowsDisplay = computed(
    () =>
      (this.generationJob()?.total_target_rows ??
        this.generationReadiness()?.total_target_rows ??
        0).toLocaleString(),
  );

  readonly generationEntitiesDisplay = computed(
    () =>
      (
        this.generationJob()?.entities?.length ??
        this.generationReadiness()?.entity_count ??
        null
      )?.toLocaleString() ?? '—',
  );

  readonly generationThroughputDisplay = computed(
    () => {
      const throughput = this.generationJob()?.throughput_rows_per_second;

      return throughput !== null && throughput !== undefined
        ? `${Math.round(throughput).toLocaleString()} rows/sec`
        : '—';
    },
  );

  readonly generationThroughputDetail = computed(
    () =>
      this.generationJob()?.throughput_rows_per_second !== null &&
      this.generationJob()?.throughput_rows_per_second !== undefined
        ? 'Measured generation throughput'
        : 'Available after execution completes',
  );

  readonly generationMetrics = computed<readonly MetricCardData[]>(() => [
    {
      label: 'Job ID',
      value: this.generationJobIdDisplay(),
      description: this.generationJobDetail(),
      icon: 'badge',
    },
    {
      label: 'Total Target Rows',
      value: this.generationTargetRowsDisplay(),
      description: 'Rows planned for generation',
      icon: 'table_rows',
    },
    {
      label: 'Entities',
      value: this.generationEntitiesDisplay(),
      description: 'Entities in generation plan',
      icon: 'account_tree',
    },
    {
      label: 'Throughput',
      value: this.generationThroughputDisplay(),
      description: this.generationThroughputDetail(),
      icon: 'speed',
    },
  ]);

  selectStep(step: WorkflowStep): void {
    if (!this.dataModelId) {
      return;
    }

    switch (step) {
      case 'model':
        this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'studio']);
        break;

      case 'validate':
        this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'validation']);
        break;

      case 'population':
        this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'population']);
        break;

      case 'generate':
        break;

      case 'results': {
        const jobId = this.generationJob()?.job_id;

        if (!jobId) {
          return;
        }

        this.router.navigate(
          ['/workspace', this.dataModelId, 'data-model', 'results', jobId],
        );
        break;
      }
    }
  }

  backToPopulation(): void {
    if (!this.dataModelId) {
      return;
    }

    this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'population']);
  }

  handlePrimaryAction(): void {
    const job = this.generationJob();

    if (job === null) {
      this.startGeneration();
      return;
    }

    if (job.status === 'CREATED') {
      this.startExistingGenerationJob(
        this.dataModelId,
        job.job_id,
        this.executionStore.getContextRevision(),
        false,
      );
      return;
    }

    if (
      job.status === 'COMPLETED' ||
      job.status === 'PARTIALLY_COMPLETED'
    ) {
      this.continueToResults();
    }
  }

  resumeGeneration(): void {
    const job = this.generationJob();
    const dataModelId = this.dataModelId;
    const revision = this.executionStore.getContextRevision();

    if (
      !dataModelId ||
      !job ||
      job.status !== 'INTERRUPTED' ||
      this.generationActionLoading() ||
      !this.executionStore.isCurrentContext(
        dataModelId,
        job.job_id,
        revision,
      )
    ) {
      return;
    }

    this.generationError.set(null);
    this.generationActionLoading.set(true);

    this.generationService
      .startGenerationJob(dataModelId, job.job_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (resumedJob) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              job.job_id,
              revision,
            )
          ) {
            return;
          }

          if (
            resumedJob.data_model_id !== dataModelId ||
            resumedJob.job_id !== job.job_id
          ) {
            this.generationActionLoading.set(false);
            this.generationError.set(
              'The backend returned a different generation job than the one requested.',
            );
            return;
          }

          this.executionStore.setJob(resumedJob, revision);
          this.executionStore.connect(dataModelId, resumedJob.job_id);
          this.loadGenerationCheckpoint(
            dataModelId,
            resumedJob.job_id,
            revision,
          );
          this.generationActionLoading.set(false);
        },
        error: (error) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              job.job_id,
              revision,
            )
          ) {
            return;
          }

          this.generationActionLoading.set(false);
          this.generationError.set(
            error?.error?.detail ??
              error?.message ??
              'Generation could not be resumed. Check the saved checkpoint and try again.',
          );
          this.loadExistingGenerationJob(dataModelId, job.job_id, revision);
        },
      });
  }

  startGeneration(): void {
    const dataModelId = this.dataModelId;
    const revision = this.executionStore.getContextRevision();

    if (
      !dataModelId ||
      this.generationJob() !== null ||
      this.generationActionLoading() ||
      !this.executionStore.isCurrentContext(dataModelId, null, revision)
    ) {
      return;
    }

    this.generationError.set(null);
    this.generationActionLoading.set(true);

    this.generationService
      .createGenerationJob(dataModelId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (job) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              null,
              revision,
            )
          ) {
            return;
          }

          if (job.data_model_id !== dataModelId || !job.job_id) {
            this.generationActionLoading.set(false);
            this.generationError.set(
              'The backend returned a generation job for an unexpected context.',
            );
            return;
          }

          this.executionStore.setJob(job, revision);

          // Keep the landing route until the backend confirms that
          // the newly created job has started.
          this.startExistingGenerationJob(
            dataModelId,
            job.job_id,
            revision,
            true,
          );
        },
        error: (error) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              null,
              revision,
            )
          ) {
            return;
          }

          this.generationActionLoading.set(false);
          this.generationError.set(
            error?.error?.detail ??
              error?.message ??
              'Unable to create the generation job.',
          );
        },
      });
  }

  /**
   * Start a persisted CREATED job, or retry a start request that failed
   * before the backend transitioned the job into execution.
   *
   * A successful initial start navigates to the job route, where route
   * restoration owns SSE and checkpoint loading. A retry already has a
   * job-specific route, so it restores those connections here.
   */
  private startExistingGenerationJob(
    dataModelId: string,
    jobId: string,
    revision: number,
    navigateOnSuccess: boolean,
  ): void {
    if (
      !dataModelId ||
      !jobId ||
      !this.executionStore.isCurrentContext(
        dataModelId,
        jobId,
        revision,
      )
    ) {
      return;
    }

    this.generationError.set(null);
    this.generationActionLoading.set(true);

    this.generationService
      .startGenerationJob(dataModelId, jobId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (startedJob) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              jobId,
              revision,
            )
          ) {
            return;
          }

          if (
            startedJob.data_model_id !== dataModelId ||
            startedJob.job_id !== jobId
          ) {
            this.generationActionLoading.set(false);
            this.generationError.set(
              'The backend returned a different generation job than the one requested.',
            );
            return;
          }

          this.executionStore.setJob(startedJob, revision);
          this.generationActionLoading.set(false);

          if (navigateOnSuccess) {
            void this.router.navigate(
              [
                '/workspace',
                dataModelId,
                'data-model',
                'generate',
                startedJob.job_id,
              ],
              { replaceUrl: true },
            );
            return;
          }

          if (
            startedJob.status === 'PREPARING' ||
            startedJob.status === 'QUEUED' ||
            startedJob.status === 'RUNNING'
          ) {
            this.executionStore.connect(dataModelId, jobId);
          }

          this.loadGenerationCheckpoint(
            dataModelId,
            jobId,
            revision,
          );
        },
        error: (error) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              jobId,
              revision,
            )
          ) {
            return;
          }

          this.generationActionLoading.set(false);
          this.generationError.set(
            error?.error?.detail ??
              error?.message ??
              'Generation job could not be started. You can retry.',
          );
        },
      });
  }

  private loadGenerationCheckpoint(
    dataModelId: string,
    jobId: string,
    revision: number,
  ): void {
    if (!dataModelId || !jobId) {
      return;
    }

    if (!this.generationCheckpoint()) {
      this.generationCheckpointLoading.set(true);
    }
    this.generationCheckpointError.set(null);

    this.generationService
      .getGenerationCheckpoint(dataModelId, jobId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (checkpoint) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              jobId,
              revision,
            )
          ) {
            return;
          }

          this.executionStore.setCheckpoint(checkpoint, revision);
          this.generationCheckpointLoading.set(false);
        },
        error: (error) => {
          if (
            !this.executionStore.isCurrentContext(
              dataModelId,
              jobId,
              revision,
            )
          ) {
            return;
          }

          this.generationCheckpointLoading.set(false);

          if (error?.status === 404) {
            this.generationCheckpoint.set(null);
            this.generationCheckpointError.set(null);
            return;
          }

          this.generationCheckpointError.set(
            error?.error?.detail ??
              error?.message ??
              'Generation checkpoint could not be loaded.',
          );
        },
      });
  }

  private isTerminalGenerationStatus(status: GenerationJobResponse['status']): boolean {
    return (
      status === 'COMPLETED' ||
      status === 'PARTIALLY_COMPLETED' ||
      status === 'FAILED' ||
      status === 'CANCELLED'
    );
  }

  continueToResults(): void {
    if (!this.dataModelId || this.generationJob() === null) {
      return;
    }

    this.router.navigate(
      [
        '/workspace',
        this.dataModelId,
        'data-model',
        'results',
        this.generationJob()!.job_id,
      ],
    );
  }
}
