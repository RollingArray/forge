import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import {
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';
import { GenerationService } from './services/generation.service';
import { GenerationExecutionStore } from './services/generation-execution.store';
import { GenerationPipelineMapper } from './services/generation-pipeline.mapper';
import { GenerationJobCardComponent } from '../../shared/components/generation-job-card/generation-job-card.component';
import { GenerationTargetCardComponent } from '../../shared/components/generation-target-card/generation-target-card.component';
import { GenerationEntitiesCardComponent } from '../../shared/components/generation-entities-card/generation-entities-card.component';
import { GenerationThroughputCardComponent } from '../../shared/components/generation-throughput-card/generation-throughput-card.component';
import { GenerationPipelineComponent } from '../../shared/components/generation-pipeline/generation-pipeline.component';
import { EntityGenerationProgressComponent } from './components/entity-generation-progress/entity-generation-progress.component';
import { GenerationJobResponse, GenerationReadiness } from './models/generation.models';

@Component({
  selector: 'app-generate',
  standalone: true,
  imports: [
    CommonModule,
    WorkflowPageComponent,
    GenerationJobCardComponent,
    GenerationTargetCardComponent,
    GenerationEntitiesCardComponent,
    GenerationThroughputCardComponent,
  GenerationPipelineComponent,
    EntityGenerationProgressComponent,
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
          ['/workspace', this.dataModelId, 'data-model', 'results'],
          { queryParams: { jobId } },
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

        this.generationService.startGenerationJob(this.dataModelId, job.job_id).subscribe({
          next: (startedJob) => {
            this.generationError.set(null);
            this.executionStore.setJob(startedJob);
            this.executionStore.connect(
              this.dataModelId,
              startedJob.job_id,
            );
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

  private isTerminalGenerationStatus(status: GenerationJobResponse['status']): boolean {
    return status === 'COMPLETED' || status === 'FAILED' || status === 'CANCELLED';
  }

  continueToResults(): void {
    if (!this.dataModelId || this.generationJob() === null) {
      return;
    }

    this.router.navigate(
      ['/workspace', this.dataModelId, 'data-model', 'results'],
      { queryParams: { jobId: this.generationJob()!.job_id } },
    );
  }
}
