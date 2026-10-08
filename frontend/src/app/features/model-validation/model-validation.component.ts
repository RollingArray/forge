import { ModelValidationSummaryComponent } from './components/model-validation-summary/model-validation-summary.component';
import { ModelValidationEntityChartComponent } from './components/model-validation-entity-chart/model-validation-entity-chart.component';
import { ModelValidationStatusChartComponent } from './components/model-validation-status-chart/model-validation-status-chart.component';
import { ModelValidationEntityTableComponent } from './components/model-validation-entity-table/model-validation-entity-table.component';
import { ModelValidationFindingsComponent } from './components/model-validation-findings/model-validation-findings.component';

import { WorkspaceHeaderComponent } from '../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../shared/components/workspace-section/workspace-section.component';

/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: model-validation.component.ts
 * Purpose: Presents deterministic validation results for a FORGE specification.
 *
 * ============================================================================
 */

import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
  OnDestroy,
  signal,
  ViewChild,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  DoughnutController,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { SpecificationService } from '../../core/services/specification.service';
import { SpecificationValidationResult } from '../../core/interfaces/specification-validation.interface';
import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import { WorkflowRowComponent } from '../../shared/components/workflow-row/workflow-row.component';
import { ForgeSpecification } from '../../core/interfaces/forge-specification.interface';
import { WorkflowActionBarComponent } from '../../shared/components/workflow-action-bar/workflow-action-bar.component';
import {
  WorkflowStepperComponent,
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';

Chart.register(
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  DoughnutController,
  Legend,
  LinearScale,
  Tooltip,
);

@Component({
  selector: 'app-model-validation',
  standalone: true,
  imports: [
    ModelValidationSummaryComponent,
    ModelValidationEntityChartComponent,
    ModelValidationStatusChartComponent,
    ModelValidationEntityTableComponent,
    ModelValidationFindingsComponent,
    WorkspaceHeaderComponent,
    WorkspaceSectionComponent,
    WorkflowPageComponent,
    WorkflowRowComponent,
    WorkflowActionBarComponent,
    WorkflowStepperComponent,
  ],
  templateUrl: './model-validation.component.html',
  styleUrl: './model-validation.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelValidationComponent
  implements AfterViewInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly specificationService = inject(SpecificationService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly changeDetectorRef = inject(ChangeDetectorRef);

  readonly steps: readonly WorkflowStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];

  readonly activeStep: WorkflowStep = 'validate';

  @ViewChild('validationChart')
  private readonly validationChart?: ElementRef<HTMLCanvasElement>;

  private validationChartInstance?: Chart<'doughnut'>;

  readonly validation = signal<SpecificationValidationResult | null>(null);
  readonly specification = signal<ForgeSpecification | null>(null);
  readonly error = signal<string | null>(null);
  readonly primaryKeyCount = computed(() =>
    this.specification()?.entities.filter(
      (entity) => (entity.identity?.fields?.length ?? 0) > 0,
    ).length ?? 0,
  );

  readonly foreignKeyCount = computed(() =>
    this.specification()?.foreignKeys.length ?? 0,
  );

  readonly compositeKeyCount = computed(() =>
    this.specification()?.entities.filter(
      (entity) => (entity.identity?.fields?.length ?? 0) > 1,
    ).length ?? 0,
  );

  readonly passRate = computed(() => {
    const result = this.validation();

    if (!result || result.totalChecks === 0) {
      return 0;
    }

    return Math.round(
      (result.passed / result.totalChecks) * 100,
    );
  });

  readonly errorCount = computed(
    () => this.validation()?.errors ?? 0,
  );

  readonly warningCount = computed(
    () => this.validation()?.warnings ?? 0,
  );

  readonly passedCount = computed(
    () => this.validation()?.passed ?? 0,
  );

  private readonly dataModelId = this.route.snapshot.paramMap.get('dataModelId');

  constructor() {
    if (!this.dataModelId) {
      this.error.set('Data Model ID is missing.');
      return;
    }

    this.loadModel(this.dataModelId);
  }

  ngAfterViewInit(): void {
    this.renderValidationChart();
  }

  ngOnDestroy(): void {
    this.validationChartInstance?.destroy();
  }

  private renderValidationChart(): void {
    const canvas = this.validationChart?.nativeElement;
    const result = this.validation();

    if (!canvas || !result) {
      return;
    }

    this.validationChartInstance?.destroy();

    this.validationChartInstance = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Passed', 'Warnings', 'Errors'],
        datasets: [
          {
            data: [
              result.passed,
              result.warnings,
              result.errors,
            ],
            backgroundColor: [
              '#12b76a',
              '#f79009',
              '#f04438',
            ],
            borderWidth: 0,
            spacing: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            enabled: true,
          },
        },
      },
    });
  }

  selectStep(step: WorkflowStep): void {
    if (!this.dataModelId) {
      return;
    }

    switch (step) {
      case 'model':
        this.backToModelStudio();
        break;

      case 'validate':
        break;

      case 'population':
        this.continueToPopulation();
        break;

      case 'generate':
        this.router.navigate([
          '/workspace',
          this.dataModelId,
          'generate',
        ]);
        break;

      case 'results':
        this.router.navigate([
          '/workspace',
          this.dataModelId,
          'results',
        ]);
        break;
    }
  }

  continueToPopulation(): void {
    if (!this.dataModelId || !this.validation()?.canContinue) {
      return;
    }

    this.router.navigate([
      '/workspace',
      this.dataModelId,
      'data-model',
      'population',
    ]);
  }

  backToModelStudio(): void {
    if (!this.dataModelId) {
      return;
    }

    this.router.navigate([
      '/workspace',
      this.dataModelId,
      'model-studio',
    ]);
  }

  private loadModel(dataModelId: string): void {
    this.specificationService
      .getSpecification(dataModelId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (specification) => {
          this.specification.set(specification);
          this.loadValidation(dataModelId);
        },
        error: () => {
          this.error.set('Unable to load the model specification.');
        },
      });
  }

  private loadValidation(dataModelId: string): void {
    this.specificationService
      .validate(dataModelId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.validation.set(result);
          this.changeDetectorRef.detectChanges();

          requestAnimationFrame(() => {
            this.renderValidationChart();
          });
        },
        error: () => {
          this.error.set('Unable to validate the model specification.');
        },
      });
  }
}
