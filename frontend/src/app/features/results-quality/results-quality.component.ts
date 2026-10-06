import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { GenerationService } from '../generate/services/generation.service';
import { GenerationJobResponse } from '../generate/models/generation.models';
import { WorkspaceService } from '../../core/services/workspace.service';

@Component({
  selector: 'app-results-quality',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './results-quality.component.html',
  styleUrl: './results-quality.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsQualityComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly generationService = inject(GenerationService);
  private readonly workspaceService = inject(WorkspaceService);
  private readonly destroyRef = inject(DestroyRef);

  readonly dataModelId =
    this.route.snapshot.paramMap.get('dataModelId') ?? '';

  readonly jobId =
    this.route.snapshot.queryParamMap.get('jobId') ?? '';

  readonly generationJob = signal<GenerationJobResponse | null>(null);
  readonly dataModelName = signal('');

  constructor() {
    this.loadGenerationJob();
    this.loadDataModel();
  }

  backToResults(): void {
    this.router.navigate(
      [
        '/workspace',
        this.dataModelId,
        'data-model',
        'results',
      ],
      {
        queryParams: {
          jobId: this.jobId,
        },
      },
    );
  }

  private loadGenerationJob(): void {
    if (!this.dataModelId || !this.jobId) {
      return;
    }

    this.generationService
      .getGenerationJob(this.dataModelId, this.jobId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (job) => this.generationJob.set(job),
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
}
