import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import {
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';
import { GenerationService } from './services/generation.service';
import { GenerationCheckpoint } from '../../shared/models/generation-checkpoint.models';
import { GenerationExecutionStore } from './services/generation-execution.store';
import { GenerationPipelineMapper } from './services/generation-pipeline.mapper';
import { GenerationSummaryCardComponent } from '../../shared/components/generation-summary-card/generation-summary-card.component';
import { GenerationPipelineComponent } from '../../shared/components/generation-pipeline/generation-pipeline.component';
import { EntityGenerationProgressComponent } from './components/entity-generation-progress/entity-generation-progress.component';
import { GenerationCheckpointComponent } from '../../shared/components/generation-checkpoint/generation-checkpoint.component';
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
    GenerationSummaryCardComponent,
  GenerationPipelineComponent,
    EntityGenerationProgressComponent,
    GenerationCheckpointComponent,
    GenerationActivityComponent,
  ],
  templateUrl: './generate.component.html',
  styleUrl: './generate.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerateComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly generationService = inject(GenerationService);
  private readonly executionStore = inject(GenerationExecutionStore);
  private readonly pipelineMapper = inject(GenerationPipelineMapper);

  readonly dataModelId = this.route.snapshot.paramMap.get('dataModelId') ?? '';
  readonly jobId = this.route.snapshot.paramMap.get('jobId') ?? '';

  readonly steps: readonly WorkflowStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];

  readonly activeStep: WorkflowStep = 'generate';

  constructor() {
    this.loadGenerationReadiness();

    if (this.jobId) {
      this.loadExistingGenerationJob(this.jobId);
    }

    effect(() => {
      const event = this.executionStore.lastEvent();

      if (event?.type === 'GENERATION_COMPLETED') {
        const job = this.executionStore.generationJob();

        if (job) {
          this.loadGenerationCheckpoint(job.job_id);
        }
      }
    });
  }

  private loadExistingGenerationJob(jobId: string): void {
    if (!this.dataModelId || !jobId) {
      return;
    }

    this.generationService
      .getGenerationJob(this.dataModelId, jobId)
      .subscribe({
        next: (job) => {
          this.executionStore.setJob(job);

          if (job.status === 'QUEUED' || job.status === 'RUNNING') {
            this.executionStore.connect(
              this.dataModelId,
              job.job_id,
            );
          }

          this.loadGenerationCheckpoint(job.job_id);
        },
        error: (error) => {
          this.generationError.set(
            error?.error?.detail ??
              error?.message ??
              'Generation job could not be loaded.',
          );
        },
      });
  }

  private loadGenerationReadiness(): void {
    if (!this.dataModelId) {
      this.generationLoading.set(false);
      this.generationError.set('Data model could not be identified.');
      return;
    }

    this.generationService.getGenerationReadiness(this.dataModelId).subscribe({
      next: (readiness) => {
        this.generationReadiness.set(readiness);
        this.generationLoading.set(false);
      },
      error: () => {
        this.generationLoading.set(false);
        this.generationError.set('Generation readiness could not be loaded.');
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
  readonly generationCheckpoint = signal<GenerationCheckpoint | null>(null);
  readonly generationCheckpointLoading = signal(false);
  readonly generationCheckpointError = signal<string | null>(null);

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
    if (this.generationJob() === null) {
      this.startGeneration();
      return;
    }

    this.continueToResults();
  }

  startGeneration(): void {
    if (!this.dataModelId || this.generationJob() !== null) {
      return;
    }

    this.generationError.set(null);

    this.generationService.createGenerationJob(this.dataModelId).subscribe({
      next: (job) => {
        this.executionStore.setJob(job);

        void this.router.navigate(
          ['/workspace', this.dataModelId, 'data-model', 'generate', job.job_id],
          { replaceUrl: true },
        );

        this.executionStore.connect(
          this.dataModelId,
          job.job_id,
        );

        this.generationService.startGenerationJob(this.dataModelId, job.job_id).subscribe({
          next: (startedJob) => {
            this.generationError.set(null);
            this.executionStore.setJob(startedJob);
            this.loadGenerationCheckpoint(startedJob.job_id);
          },
          error: (error) => {
            const message =
              error?.error?.detail ?? error?.message ?? 'Generation job could not be started.';

            this.generationError.set(message);
          },
        });
      },
      error: (error) => {
        const message =
          error?.error?.detail ?? error?.message ?? 'Unable to create the generation job.';

        this.generationError.set(message);
      },
    });
  }

  private loadGenerationCheckpoint(jobId: string): void {
    if (!this.dataModelId || !jobId) {
      return;
    }

    this.generationCheckpointLoading.set(true);
    this.generationCheckpointError.set(null);

    this.generationService
      .getGenerationCheckpoint(this.dataModelId, jobId)
      .subscribe({
        next: (checkpoint) => {
          this.generationCheckpoint.set(checkpoint);
          this.generationCheckpointLoading.set(false);
        },
        error: (error) => {
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
    return status === 'COMPLETED' || status === 'FAILED' || status === 'CANCELLED';
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
