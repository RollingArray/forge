import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { ForgeNavigationService } from '../../core/navigation/forge-navigation.service';


import { SidebarComponent } from '../home/components/sidebar/sidebar.component';
import { StudioHeaderComponent } from '../model-studio/components/studio-header/studio-header.component';
import { WorkflowStepperComponent } from '../model-studio/components/workflow-stepper/workflow-stepper.component';

import {
  PopulationSummaryComponent,
  PopulationSummaryItem,
} from './components/population-summary/population-summary.component';

import {
  PopulationFeasibilityComponent,
} from './components/population-feasibility/population-feasibility.component';

import {
  EntityPopulationTableComponent,
  PopulationRequestedChange,
} from './components/entity-population-table/entity-population-table.component';

import {
  PopulationStatus,
  PopulationTableRow,
  PopulationInsight,
} from './models/population-plan.models';

import {
  RelationshipCapacityComponent,
} from './components/relationship-capacity/relationship-capacity.component';

import {
  HierarchyCardinalityComponent,
} from './components/hierarchy-cardinality/hierarchy-cardinality.component';

import {
  PopulationCardinalityItem,
  PopulationHierarchyNode,
} from './models/population-plan.models';

import {
  PopulationOverviewComponent,
} from './components/population-overview/population-overview.component';

import {
  PopulationInsightsComponent,
} from './components/population-insights/population-insights.component';

import {
  PopulationActionsComponent,
} from './components/population-actions/population-actions.component';

import {
  ForgeSpecification,
  ModelRelationship,
  StudioStep,
} from '../model-studio/models/model-studio.models';

import {
  PopulationPlan,
} from './models/population-plan.models';

import {
  adaptPopulationPlan,
} from './data/population-plan-adapter';

import {
  buildRelationships,
} from '../model-studio/data/specification-adapter';

@Component({
  selector: 'app-population-plan',
  standalone: true,
  imports: [
    SidebarComponent,
    StudioHeaderComponent,
    WorkflowStepperComponent,
    PopulationSummaryComponent,
    PopulationFeasibilityComponent,
    EntityPopulationTableComponent,
    RelationshipCapacityComponent,
    PopulationOverviewComponent,
    PopulationInsightsComponent,
    PopulationActionsComponent,
    HierarchyCardinalityComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './population-plan.component.html',
  styleUrl: './population-plan.component.css',
})
export class PopulationPlanComponent {
  private readonly navigation = inject(ForgeNavigationService);

  readonly steps = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ] as const;

  readonly activeStep = signal<StudioStep>('population');

  readonly specification =
    signal<ForgeSpecification | null>(null);

  readonly populationPlan =
    signal<PopulationPlan | null>(null);

  readonly isLoading =
    signal(true);

  readonly loadError =
    signal<string | null>(null);

  readonly entityCount = computed(
    () =>
      Object.keys(
        this.populationPlan()?.populations ?? {},
      ).length,
  );

  readonly totalResolvedRecords = computed(
    () =>
      Object.values(
        this.populationPlan()?.populations ?? {},
      ).reduce(
        (total, population) =>
          total + (population.resolved ?? 0),
        0,
      ),
  );

  readonly feasibleCount = computed(
    () =>
      Object.values(
        this.populationPlan()?.populations ?? {},
      ).filter(
        population =>
          population.status === 'FEASIBLE',
      ).length,
  );

  readonly summaryItems = computed<
    readonly PopulationSummaryItem[]
  >(() => [
    {
      label: 'Entities',
      value: this.entityCount(),
      icon: 'database',
    },
    {
      label: 'Planned Records',
      value: this.totalResolvedRecords(),
      icon: 'table_rows',
    },
    {
      label: 'Feasible Entities',
      value: this.feasibleCount(),
      icon: 'check_circle',
    },
    {
      label: 'Capacity Constraints',
      value:
        this.populationPlan()?.capacityLimits.length ?? 0,
      icon: 'speed',
    },
  ]);

  readonly populationInsights = computed<
    readonly PopulationInsight[]
  >(() => {
    const plan = this.populationPlan();

    if (!plan) {
      return [];
    }

    const insights: PopulationInsight[] = [];

    const populations = Object.entries(
      plan.populations,
    );

    const minimumBoundEntities = populations.filter(
      ([entity, population]) =>
        population.resolved !== null &&
        plan.minimums[entity] !== undefined &&
        population.resolved === plan.minimums[entity],
    );

    if (minimumBoundEntities.length > 0) {
      insights.push({
        type: 'constraint',
        title: 'Minimum-feasible populations',
        message:
          `${minimumBoundEntities.length} entities are resolved at their derived minimum feasible population.`,
      });
    }

    if (plan.capacityRequirements.length > 0) {
      insights.push({
        type: 'capacity',
        title: 'Capacity requirements detected',
        message:
          `${plan.capacityRequirements.length} capacity requirement${plan.capacityRequirements.length === 1 ? '' : 's'} were derived from the model relationships.`,
      });
    }

    if (plan.capacityLimits.length > 0) {
      const limitedEntities = plan.capacityLimits
        .map(limit => limit.entity)
        .join(', ');

      insights.push({
        type: 'capacity',
        title: 'Capacity limits detected',
        message:
          `${plan.capacityLimits.length} capacity limit${plan.capacityLimits.length === 1 ? '' : 's'} apply to ${limitedEntities}.`,
      });
    }

    const largest = populations
      .filter(
        ([, population]) =>
          population.resolved !== null &&
          population.resolved > 0,
      )
      .sort(
        ([, a], [, b]) =>
          (b.resolved ?? 0) -
          (a.resolved ?? 0),
      )[0];

    if (largest) {
      insights.push({
        type: 'population',
        title: 'Largest planned population',
        message:
          `${largest[0]} has the largest resolved population at ${(largest[1].resolved ?? 0).toLocaleString()} records.`,
        entity: largest[0],
      });
    }

    const autoCount = populations.filter(
      ([, population]) =>
        population.mode === 'AUTO',
    ).length;

    if (autoCount > 0) {
      insights.push({
        type: 'info',
        title: 'Automatic population resolution',
        message:
          `${autoCount} entities use automatic population resolution.`,
      });
    }

    return insights;
  });

  readonly populationRelationships = computed<
    readonly ModelRelationship[]
  >(() => {
    const specification = this.specification();

    if (!specification) {
      return [];
    }

    return buildRelationships(specification);
  });

  readonly hierarchyNodes = computed<
    readonly PopulationHierarchyNode[]
  >(() => {
    const plan = this.populationPlan();

    if (!plan) {
      return [];
    }

    const relationships =
      this.populationRelationships();

    const entities =
      Object.keys(plan.populations);

    const children = new Map<string, string[]>();
    const hasParent = new Set<string>();

    for (const relationship of relationships) {
      if (
        relationship.type !== 'ONE_TO_MANY'
      ) {
        continue;
      }

      const source =
        relationship.source;

      const target =
        relationship.target;

      const targetList =
        children.get(source) ?? [];

      targetList.push(target);
      children.set(source, targetList);
      hasParent.add(target);
    }

    const levels = new Map<string, number>();

    for (const entity of entities) {
      if (!hasParent.has(entity)) {
        levels.set(entity, 0);
      }
    }

    const queue = [...levels.keys()];

    while (queue.length > 0) {
      const parent = queue.shift()!;
      const parentLevel =
        levels.get(parent) ?? 0;

      for (
        const child of children.get(parent) ?? []
      ) {
        const nextLevel =
          parentLevel + 1;

        if (
          !levels.has(child) ||
          nextLevel > levels.get(child)!
        ) {
          levels.set(child, nextLevel);
          queue.push(child);
        }
      }
    }

    return entities
      .map(entity => ({
        entity,
        level: levels.get(entity) ?? 0,
        resolved:
          plan.populations[entity]?.resolved ?? 0,
        relationshipCount:
          relationships.filter(
            relationship =>
              relationship.source === entity ||
              relationship.target === entity,
          ).length,
      }))
      .sort(
        (a, b) =>
          a.level - b.level ||
          a.entity.localeCompare(b.entity),
      );
  });

  readonly cardinalityItems = computed<
    readonly PopulationCardinalityItem[]
  >(() =>
    this.populationRelationships().map(
      relationship => ({
        source: relationship.source,
        target: relationship.target,
        type: relationship.type,
        sourceCardinality:
          relationship.sourceCardinality,
        targetCardinality:
          relationship.targetCardinality,
        sourceParticipation:
          relationship.sourceParticipation,
        targetParticipation:
          relationship.targetParticipation,
        sourceFields:
          relationship.sourceFields,
        targetFields:
          relationship.targetFields,
      }),
    ),
  );

  readonly populationRows = computed<
    readonly PopulationTableRow[]
  >(() => {
    const plan = this.populationPlan();

    if (!plan) {
      return [];
    }

    return Object.entries(plan.populations).map(
      ([entity, population]) => ({
        entity,
        mode: population.mode,
        requested: population.requested,
        minimumFeasible:
          population.minimumFeasible,
        maximumFeasible:
          plan.maximums[entity] ?? null,
        resolved: population.resolved,
        status: population.status,
        reason: population.reason,
        recommendation:
          population.recommendation,
      }),
    );
  });

  readonly feasibilityStatus = computed<PopulationStatus>(() => {
    const populations = Object.values(
      this.populationPlan()?.populations ?? {},
    );

    if (
      populations.some(
        population =>
          population.status === 'INFEASIBLE',
      )
    ) {
      return 'INFEASIBLE';
    }

    if (
      populations.some(
        population =>
          population.status === 'WARNING',
      )
    ) {
      return 'WARNING';
    }

    return 'FEASIBLE';
  });

  readonly feasibilityTitle = computed(() => {
    switch (this.feasibilityStatus()) {
      case 'INFEASIBLE':
        return 'Population plan is not feasible';

      case 'WARNING':
        return 'Population plan has warnings';

      default:
        return 'Population plan is feasible';
    }
  });

  readonly feasibilityMessage = computed(() => {
    switch (this.feasibilityStatus()) {
      case 'INFEASIBLE':
        return 'One or more requested populations exceed the derived feasible bounds.';

      case 'WARNING':
        return 'The population plan contains conditions that should be reviewed before generation.';

      default:
        return 'All populations can be generated within the derived feasibility bounds.';
    }
  });

  handlePopulationAction(action: string): void {
    switch (action) {
      case 'back':
        this.selectStep('model');
        break;

      case 'review-accept':
        this.selectStep('generate');
        break;
    }
  }

  constructor() {
    this.loadData();
  }

  private async loadData(): Promise<void> {
    this.isLoading.set(true);
    this.loadError.set(null);

    try {
      const [
        specificationResponse,
        populationResponse,
      ] = await Promise.all([
        fetch('/specification.json'),
        fetch('/population_plan.json'),
      ]);

      if (!specificationResponse.ok) {
        throw new Error(
          `Unable to load specification: ${specificationResponse.status}`,
        );
      }

      if (!populationResponse.ok) {
        throw new Error(
          `Unable to load population plan: ${populationResponse.status}`,
        );
      }

      const specification =
        (await specificationResponse.json()) as ForgeSpecification;

      const rawPopulationPlan =
        await populationResponse.json();

      this.specification.set(
        specification,
      );

      this.populationPlan.set(
        adaptPopulationPlan(
          rawPopulationPlan,
        ),
      );
    } catch (error) {
      console.error(
        '[FORGE Population Plan] load failed',
        error,
      );

      this.loadError.set(
        error instanceof Error
          ? error.message
          : 'Unable to load population plan.',
      );
    } finally {
      this.isLoading.set(false);
    }
  }

  selectStep(step: StudioStep): void {
    this.activeStep.set(step);
    this.navigation.navigateToStep(step);
  }

  updateRequestedPopulation(
    change: PopulationRequestedChange,
  ): void {
    console.info(
      '[FORGE Population Plan] requested population changed',
      change,
    );
  }

}
