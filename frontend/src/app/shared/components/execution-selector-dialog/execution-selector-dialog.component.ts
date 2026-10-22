import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { catchError, finalize, of } from 'rxjs';

import { GenerationService } from '../../../features/generate/services/generation.service';
import {
  ExecutionContextDataModel,
  ExecutionContextJob,
} from '../../../features/generate/models/generation.models';
import { ContentCardComponent } from '../content-card/content-card.component';
import { ContentGridComponent } from '../content-grid/content-grid.component';
import { FormDialogComponent } from '../form-dialog/form-dialog.component';

export type ExecutionSelectorDestination =
  | 'executions'
  | 'generated-data'
  | 'quality-analysis'
  | 'validation-analysis';

export interface ExecutionSelection {
  dataModelId: string;
  jobId: string;
  destination: ExecutionSelectorDestination;
}

@Component({
  selector: 'app-execution-selector-dialog',
  standalone: true,
  imports: [
    DatePipe,
    DecimalPipe,
    ContentGridComponent,
    ContentCardComponent,
    FormDialogComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './execution-selector-dialog.component.html',
  styleUrl: './execution-selector-dialog.component.css',
})
export class ExecutionSelectorDialogComponent {
  readonly open = input(false);
  readonly destination = input<ExecutionSelectorDestination>('executions');
  readonly closed = output<void>();
  readonly selectionConfirmed = output<ExecutionSelection>();

  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly generationService = inject(GenerationService);

  readonly models = signal<ExecutionContextDataModel[]>([]);
  readonly modelId = signal('');
  readonly jobId = signal('');
  readonly loadingModels = signal(false);
  readonly error = signal<string | null>(null);

  private readonly loadWhenOpened = effect(() => {
    if (this.open()) {
      this.loadExecutionContext();
    }
  });

  selectJob(dataModelId: string, jobId: string): void {
    this.modelId.set(dataModelId);
    this.jobId.set(jobId);
    this.error.set(null);
  }

  confirmSelection(): void {
    const dataModelId = this.modelId();
    const jobId = this.jobId();
    const selectedModel = this.models().find(
      (model) => model.data_model_id === dataModelId,
    );

    if (
      !dataModelId ||
      !jobId ||
      !selectedModel?.jobs.some((job) => job.job_id === jobId)
    ) {
      this.error.set('Select a data model and one of its generation jobs.');
      return;
    }

    this.selectionConfirmed.emit({
      dataModelId,
      jobId,
      destination: this.destination(),
    });
  }

  private loadExecutionContext(): void {
    this.error.set(null);
    this.models.set([]);
    this.modelId.set('');
    this.jobId.set('');
    this.loadingModels.set(true);

    const segments = this.router.url
      .split('?')[0]
      .split('#')[0]
      .split('/')
      .filter(Boolean);
    const workspaceIndex = segments.indexOf('workspace');
    const routeModelId =
      workspaceIndex >= 0 ? segments[workspaceIndex + 1] : '';
    const resultsIndex = segments.indexOf('results');
    const generateIndex = segments.indexOf('generate');
    const routeJobId =
      resultsIndex >= 0
        ? segments[resultsIndex + 1]
        : generateIndex >= 0
          ? segments[generateIndex + 1]
          : '';

    this.generationService
      .getExecutionContext()
      .pipe(
        catchError(() => {
          this.error.set(
            'Unable to load execution context. Please try again.',
          );
          return of(null);
        }),
        finalize(() => {
          this.loadingModels.set(false);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((context) => {
        if (!context) {
          return;
        }

        const models = context.data_models;
        this.models.set(models);

        const selectedModelId = models.some(
          (model) => model.data_model_id === routeModelId,
        )
          ? routeModelId
          : '';
        this.modelId.set(selectedModelId);

        const selectedModel = models.find(
          (model) => model.data_model_id === selectedModelId,
        );
        const jobs = selectedModel?.jobs ?? [];
        this.jobId.set(
          jobs.some((job) => job.job_id === routeJobId) ? routeJobId : '',
        );
      });
  }
}
