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
import { ForgeSpecification } from '../../core/interfaces/forge-specification.interface';
import { WorkflowActionBarComponent } from '../../shared/components/workflow-action-bar/workflow-action-bar.component';
import {
  WorkflowStepperComponent,
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';

export type ValidationFilter = 'all' | 'error' | 'warning' | 'passed';

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

  @ViewChild('entityValidationChart')
  private readonly entityValidationChart?: ElementRef<HTMLCanvasElement>;

  private validationChartInstance?: Chart<'doughnut'>;
  private entityValidationChartInstance?: Chart<'bar'>;

  readonly validation = signal<SpecificationValidationResult | null>(null);
  readonly specification = signal<ForgeSpecification | null>(null);
  readonly error = signal<string | null>(null);
  readonly activeFilter = signal<ValidationFilter>('all');
  readonly searchQuery = signal('');

  readonly filteredFindings = computed(() => {
    const findings = this.validation()?.findings ?? [];
    const filter = this.activeFilter();
    const query = this.searchQuery().trim().toLowerCase();

    return findings.filter((finding) => {
      const matchesFilter =
        filter === 'all' || finding.severity === filter;

      if (!matchesFilter) {
        return false;
      }

      if (!query) {
        return true;
      }

      return [
        finding.category,
        finding.title,
        finding.details,
        finding.entity ?? '',
        finding.field ?? '',
      ]
        .join(' ')
        .toLowerCase()
        .includes(query);
    });
  });

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

  readonly entityErrorCount = computed(
    () =>
      this.validation()?.entities.filter(
        (entity) => entity.errors > 0,
      ).length ?? 0,
  );

  readonly entityWarningCount = computed(
    () =>
      this.validation()?.entities.filter(
        (entity) =>
          entity.errors === 0 && entity.warnings > 0,
      ).length ?? 0,
  );

  readonly entityValidCount = computed(
    () =>
      this.validation()?.entities.filter(
        (entity) =>
          entity.errors === 0 &&
          entity.warnings === 0,
      ).length ?? 0,
  );

  readonly maxEntityChecks = computed(() => {
    const entities = this.validation()?.entities ?? [];

    return Math.max(
      ...entities.map((entity) => entity.checks),
      1,
    );
  });

  entityBarWidth(checks: number): number {
    return Math.max(
      8,
      Math.round(
        (checks / this.maxEntityChecks()) * 100,
      ),
    );
  }

  filterCount(filter: ValidationFilter): number {
    const result = this.validation();

    if (!result) {
      return 0;
    }

    if (filter === 'all') {
      return result.findings.length;
    }

    return result.findings.filter(
      (finding) => finding.severity === filter,
    ).length;
  }

  updateSearch(event: Event): void {
    this.searchQuery.set(
      (event.target as HTMLInputElement).value,
    );
  }

  clearSearch(): void {
    this.searchQuery.set('');
  }

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
    this.entityValidationChartInstance?.destroy();
  }

  private renderEntityValidationChart(): void {
    const canvas = this.entityValidationChart?.nativeElement;
    const result = this.validation();

    if (!canvas || !result) return;

    this.entityValidationChartInstance?.destroy();

    const passedGradient = canvas
      .getContext('2d')!
      .createLinearGradient(0, 0, 0, 420);
    passedGradient.addColorStop(0, '#12b76a');
    passedGradient.addColorStop(1, '#6ce9a6');

    const warningGradient = canvas
      .getContext('2d')!
      .createLinearGradient(0, 0, 0, 420);
    warningGradient.addColorStop(0, '#f79009');
    warningGradient.addColorStop(1, '#fdb022');

    const errorGradient = canvas
      .getContext('2d')!
      .createLinearGradient(0, 0, 0, 420);
    errorGradient.addColorStop(0, '#f04438');
    errorGradient.addColorStop(1, '#f97066');

    this.entityValidationChartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: result.entities.map((entity) => entity.name),
        datasets: [
          {
            label: 'Passed',
            data: result.entities.map(
              (entity) => entity.checks - entity.errors - entity.warnings,
            ),
            backgroundColor: passedGradient,
            borderRadius: (context) => {
              const entity = result.entities[context.dataIndex];
              const hasWarnings = entity.warnings > 0;
              const hasErrors = entity.errors > 0;

              return {
                topLeft: !hasWarnings && !hasErrors ? 12 : 0,
                topRight: !hasWarnings && !hasErrors ? 12 : 0,
                bottomLeft: 12,
                bottomRight: 12,
              };
            },
            borderSkipped: false,
            stack: 'checks',
          },
          {
            label: 'Warnings',
            data: result.entities.map((entity) => entity.warnings),
            backgroundColor: warningGradient,
            borderRadius: (context) => {
              const entity = result.entities[context.dataIndex];
              const isOnlySegment =
                entity.warnings > 0 &&
                entity.errors === 0 &&
                entity.checks - entity.errors - entity.warnings === 0;

              return {
                topLeft: isOnlySegment ? 12 : 0,
                topRight: isOnlySegment ? 12 : 0,
                bottomLeft: isOnlySegment ? 12 : 0,
                bottomRight: isOnlySegment ? 12 : 0,
              };
            },
            borderSkipped: false,
            stack: 'checks',
          },
          {
            label: 'Errors',
            data: result.entities.map((entity) => entity.errors),
            backgroundColor: errorGradient,
            borderRadius: (context) => {
              const entity = result.entities[context.dataIndex];
              const hasPassed =
                entity.checks - entity.errors - entity.warnings > 0;
              const hasWarnings = entity.warnings > 0;

              return {
                topLeft: 12,
                topRight: 12,
                bottomLeft: !hasPassed && !hasWarnings ? 12 : 0,
                bottomRight: !hasPassed && !hasWarnings ? 12 : 0,
              };
            },
            borderSkipped: false,
            stack: 'checks',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            stacked: true,
            grid: {
              display: false,
            },
            border: {
              display: false,
            },
            ticks: {
              autoSkip: false,
              maxRotation: 60,
              minRotation: 45,
            },
          },
          y: {
            stacked: true,
            beginAtZero: true,
            grid: {
              display: false,
            },
            border: {
              display: false,
            },
            ticks: {
              precision: 0,
            },
            title: {
              display: true,
              text: 'Checks',
            },
          },
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
          },
          tooltip: {
            enabled: true,
          },
        },
      },
    });
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

  setFilter(filter: ValidationFilter): void {
    this.activeFilter.set(filter);
  }

  continueToPopulation(): void {
    if (!this.dataModelId || !this.validation()?.canContinue) {
      return;
    }

    this.router.navigate([
      '/workspace',
      this.dataModelId,
      'population-plan',
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
            this.renderEntityValidationChart();
          });
        },
        error: () => {
          this.error.set('Unable to validate the model specification.');
        },
      });
  }
}
