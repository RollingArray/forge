import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import {
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { GenerationService } from '../generate/services/generation.service';
import { WorkspaceService } from '../../core/services/workspace.service';
import { GenerationJobResponse } from '../generate/models/generation.models';
import {
  GenerationArtifact,
  GenerationArtifactPreview,
} from './results.models';

import { ResultsExecutionSummaryComponent } from './components/results-execution-summary/results-execution-summary.component';
import { GeneratedFilesComponent } from './components/generated-files/generated-files.component';
import { ArtifactPreviewComponent } from './components/artifact-preview/artifact-preview.component';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [
    CommonModule,
    WorkflowPageComponent,
    ResultsExecutionSummaryComponent,
    GeneratedFilesComponent,
    ArtifactPreviewComponent,
  ],
  templateUrl: './results.component.html',
  styleUrl: './results.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly generationService = inject(GenerationService);
  private readonly workspaceService = inject(WorkspaceService);
  private readonly destroyRef = inject(DestroyRef);

  readonly dataModelId =
    this.route.snapshot.paramMap.get('dataModelId') ?? '';

  readonly jobId =
    this.route.snapshot.queryParamMap.get('jobId') ?? '';

  readonly steps: readonly WorkflowStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];

  readonly activeStep: WorkflowStep = 'results';

  readonly generationJob = signal<GenerationJobResponse | null>(null);
  readonly dataModelName = signal('');

  readonly artifacts = signal<GenerationArtifact[]>([]);
  readonly filteredArtifacts = signal<GenerationArtifact[]>([]);
  readonly artifactsLoading = signal(true);
  readonly artifactsError = signal<string | null>(null);

  readonly selectedArtifact = signal<GenerationArtifact | null>(null);
  readonly preview = signal<GenerationArtifactPreview | null>(null);
  readonly previewLoading = signal(false);
  readonly previewError = signal<string | null>(null);

  readonly searchTerm = signal('');

  constructor() {
    this.loadGenerationJob();
    this.loadDataModel();
    this.loadArtifacts();
  }

  selectStep(step: WorkflowStep): void {
    if (!this.dataModelId) {
      return;
    }

    switch (step) {
      case 'model':
        this.router.navigate([
          '/workspace',
          this.dataModelId,
          'data-model',
          'studio',
        ]);
        break;

      case 'validate':
        this.router.navigate([
          '/workspace',
          this.dataModelId,
          'data-model',
          'validation',
        ]);
        break;

      case 'population':
        this.router.navigate([
          '/workspace',
          this.dataModelId,
          'data-model',
          'population',
        ]);
        break;

      case 'generate':
        this.router.navigate([
          '/workspace',
          this.dataModelId,
          'data-model',
          'generate',
        ]);
        break;

      case 'results':
        break;
    }
  }

  updateSearchTerm(value: string): void {
    const term = value.trim().toLowerCase();
    this.searchTerm.set(value);

    this.filteredArtifacts.set(
      this.artifacts().filter((artifact) =>
        artifact.filename.toLowerCase().includes(term),
      ),
    );
  }

  selectArtifact(artifact: GenerationArtifact): void {
    this.selectedArtifact.set(artifact);
    this.preview.set(null);
    this.previewError.set(null);
    this.previewLoading.set(true);

    this.generationService
      .getGenerationArtifactPreview(
        this.dataModelId,
        this.jobId,
        artifact.entity_name,
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (preview) => {
          this.preview.set(preview);
          this.previewLoading.set(false);
        },
        error: () => {
          this.previewError.set(
            'The file preview could not be loaded.',
          );
          this.previewLoading.set(false);
        },
      });
  }

  downloadArtifact(artifact: GenerationArtifact): void {
    this.generationService
      .downloadGenerationArtifact(
        this.dataModelId,
        this.jobId,
        artifact.entity_name,
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement('a');

          anchor.href = url;
          anchor.download = artifact.filename;
          anchor.click();

          URL.revokeObjectURL(url);
        },
      });
  }

  backToGenerate(): void {
    if (!this.dataModelId) {
      return;
    }

    this.router.navigate([
      '/workspace',
      this.dataModelId,
      'data-model',
      'generate',
    ]);
  }

  private loadGenerationJob(): void {
    if (!this.dataModelId || !this.jobId) {
      return;
    }

    this.generationService
      .getGenerationJob(this.dataModelId, this.jobId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (job) => {
          this.generationJob.set(job);
        },
      });
  }

  private loadDataModel(): void {
    if (!this.dataModelId) {
      return;
    }

    this.workspaceService
      .getDataModels()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (dataModels) => {
          const dataModel = dataModels.find(
            (model) => model.dataModelId === this.dataModelId,
          );

          this.dataModelName.set(dataModel?.name ?? '');
        },
      });
  }

  private loadArtifacts(): void {
    if (!this.dataModelId || !this.jobId) {
      this.artifactsLoading.set(false);
      this.artifactsError.set(
        'The generation job could not be identified.',
      );
      return;
    }

    this.generationService
      .getGenerationArtifacts(
        this.dataModelId,
        this.jobId,
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (artifacts) => {
          this.artifacts.set(artifacts);
          this.filteredArtifacts.set(artifacts);
          this.artifactsLoading.set(false);

          if (artifacts.length > 0) {
            this.selectArtifact(artifacts[0]);
          }
        },
        error: () => {
          this.artifactsError.set(
            'Generated files could not be loaded.',
          );
          this.artifactsLoading.set(false);
        },
      });
  }
}
