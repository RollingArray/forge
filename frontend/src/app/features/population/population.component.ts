/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: population.component.ts
 * Purpose: Presents and configures the population plan for a FORGE model.
 *
 * ============================================================================
 */

import { DecimalPipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { PopulationService } from './services/population.service';
import { EntityPopulationTableComponent } from './components/entity-population-table/entity-population-table.component';
import { PopulationSummaryComponent } from './components/population-summary/population-summary.component';
import { PopulationTargetComponent } from './components/population-target/population-target.component';
import { PopulationCandidateDecisionComponent } from './components/population-candidate-decision/population-candidate-decision.component';
import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import { WorkflowRowComponent } from '../../shared/components/workflow-row/workflow-row.component';
import {
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';
import {
  PopulationCandidatePlan,
} from './models/population.models';

@Component({
  selector: 'app-population',
  standalone: true,
  imports: [
    WorkflowPageComponent,
    WorkflowRowComponent,
    DecimalPipe,
    EntityPopulationTableComponent,
    PopulationSummaryComponent,
    PopulationTargetComponent,
    PopulationCandidateDecisionComponent,
  ],
  templateUrl: './population.component.html',
  styleUrl: './population.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PopulationComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly populationService = inject(PopulationService);

  readonly steps: readonly WorkflowStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];

  readonly activeStep: WorkflowStep = 'population';

  readonly dataModelId =
    this.route.snapshot.paramMap.get('dataModelId') ?? '';

  readonly populationPlan = toSignal(
    this.populationService.getPopulationPlan(this.dataModelId),
    { initialValue: null },
  );

  readonly candidatePlan = signal<PopulationCandidatePlan | null>(null);

  readonly displayedPlan = computed(
    () => this.candidatePlan() ?? this.populationPlan(),
  );

  readonly driverOptions = computed(() =>
    Object.keys(this.populationPlan()?.populations ?? {}),
  );

  readonly selectedDriver = signal<string | null>(null);

  readonly entityCount = computed(
    () => Object.keys(this.displayedPlan()?.populations ?? {}).length,
  );

  readonly targetRows = signal<number | null>(null);

  readonly resolvedRows = computed(
    () =>
      Object.values(this.displayedPlan()?.populations ?? {}).reduce(
        (total, population) => total + (population.resolved ?? 0),
        0,
      ),
  );

  readonly gapRows = computed(() => {
    const target = this.targetRows();

    if (target === null) {
      return null;
    }

    return target - this.resolvedRows();
  });

  readonly feasibleCount = computed(
    () =>
      Object.values(this.displayedPlan()?.populations ?? {}).filter(
        (population) => population.status === 'FEASIBLE',
      ).length,
  );

  readonly isCandidate = computed(() => this.candidatePlan() !== null);

  readonly candidateFeasible = computed(
    () => this.candidatePlan()?.feasible ?? false,
  );

  readonly isDistributing = signal(false);

  readonly errorMessage = signal<string | null>(null);

  setTarget(value: string): void {
    const target = Number(value);

    this.errorMessage.set(null);
    this.candidatePlan.set(null);

    if (!Number.isFinite(target) || target <= 0) {
      this.targetRows.set(null);
      return;
    }

    this.targetRows.set(Math.floor(target));
  }

  setDriver(driver: string): void {
    this.errorMessage.set(null);
    this.candidatePlan.set(null);

    this.selectedDriver.set(driver || null);
  }

  distributeTarget(): void {
    const target = this.targetRows();
    const driver = this.selectedDriver() ?? this.driverOptions()[0] ?? null;

    if (!this.dataModelId || target === null || driver === null) {
      return;
    }

    this.selectedDriver.set(driver);
    this.errorMessage.set(null);
    this.isDistributing.set(true);

    this.populationService
      .buildCandidatePlan(this.dataModelId, target, driver)
      .subscribe({
        next: (candidate) => {
          this.candidatePlan.set(candidate);
          this.isDistributing.set(false);
        },
        error: (error: { error?: { detail?: string } }) => {
          this.candidatePlan.set(null);
          this.isDistributing.set(false);
          this.errorMessage.set(
            error.error?.detail ?? 'Failed to distribute the population target.',
          );
        },
      });
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
        this.router.navigate([
          '/workspace',
          this.dataModelId,
          'data-model',
          'results',
        ]);
        break;
    }
  }

  backToValidation(): void {
    if (!this.dataModelId) {
      return;
    }

    this.router.navigate([
      '/workspace',
      this.dataModelId,
      'data-model',
      'validation',
    ]);
  }

  reviewAndAcceptPlan(): void {
    const candidate = this.candidatePlan();
    const plan = this.displayedPlan();

    if (!this.dataModelId || !plan) {
      return;
    }

    if (candidate && !candidate.feasible) {
      return;
    }

    const populations = Object.fromEntries(
      Object.entries(plan.populations).map(
        ([entity, population]) => [
          entity,
          population.resolved ?? 0,
        ],
      ),
    );

    this.errorMessage.set(null);
    this.isDistributing.set(true);

    this.populationService
      .acceptPopulationPlan(
        this.dataModelId,
        populations,
      )
      .subscribe({
        next: () => {
          this.isDistributing.set(false);

          this.router.navigate([
            '/workspace',
            this.dataModelId,
            'data-model',
            'generate',
          ]);
        },
        error: (error: { error?: { detail?: string } }) => {
          this.isDistributing.set(false);
          this.errorMessage.set(
            error.error?.detail ??
              'Failed to accept the population plan.',
          );
        },
      });
  }
}
