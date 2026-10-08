import { DecimalPipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  TemplateRef,
  computed,
  input,
  viewChild,
} from '@angular/core';

import {
  PopulationEntityPlan,
  PopulationPlan,
} from '../../models/population.models';

import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceSimpleTableComponent } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.component';
import {
  WorkspaceSimpleTableCellContext,
  WorkspaceSimpleTableColumn,
} from '../../../../shared/components/workspace-simple-table/workspace-simple-table.models';

interface PopulationTableRow {
  entity: string;
  scaling: PopulationEntityPlan['scaling'];
  minimumAllowed: number | null;
  original: number | null;
  proposed: number | null;
  change: number | null;
  changePercent: number | null;
  changeBarWidth: number;
  planned: number | null;
  status: PopulationEntityPlan['status'];
}
@Component({
  selector: 'app-entity-population-table',
  standalone: true,
  imports: [
    DecimalPipe,
    WorkspaceHeaderComponent,
    WorkspaceSectionComponent,
    WorkspaceSimpleTableComponent,
  ],
  templateUrl: './entity-population-table.component.html',
  styleUrl: './entity-population-table.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityPopulationTableComponent {
  readonly plan = input.required<PopulationPlan>();
  readonly originalPlan = input.required<PopulationPlan>();

  readonly changeTemplate =
    viewChild<TemplateRef<WorkspaceSimpleTableCellContext<PopulationTableRow>>>(
      'changeTemplate',
    );

  readonly columns = computed<
    readonly WorkspaceSimpleTableColumn<PopulationTableRow>[]
  >(() => {
    const changeTemplate = this.changeTemplate();

    return [
      {
        key: 'entity',
        label: '#',
        type: 'index',
        width: '48px',
        align: 'center',
      },
      {
        key: 'entity',
        label: 'Entity',
        width: 'minmax(180px, 1fr)',
      },
      {
        key: 'scaling',
        label: 'Scaling',
        width: '110px',
        align: 'center',
      },
      {
        key: 'minimumAllowed',
        label: 'Minimum Allowed',
        width: '130px',
        align: 'center',
      },
      {
        key: 'original',
        label: 'Current',
        width: '100px',
        align: 'center',
      },
      {
        key: 'proposed',
        label: 'Proposed',
        width: '110px',
        align: 'center',
      },
      {
        key: 'change',
        label: 'Change',
        width: '150px',
        align: 'center',
        template: changeTemplate,
      },
      {
        key: 'planned',
        label: 'Planned',
        width: '110px',
        align: 'center',
      },
      {
        key: 'status',
        label: 'Status',
        width: '120px',
        align: 'center',
      },
    ];
  });

  readonly rows = computed<PopulationTableRow[]>(() => {
    const originalPopulations = this.originalPlan().populations;

    const rawRows = Object.entries(this.plan().populations).map(
      ([entity, population]) => {
        const original = originalPopulations[entity]?.resolved ?? null;
        const candidate = population.resolved;

        const change =
          original !== null && candidate !== null
            ? candidate - original
            : null;

        const changePercent =
          original !== null && original !== 0 && change !== null
            ? (change / original) * 100
            : null;

        return {
          entity,
          scaling: population.scaling,
          minimumAllowed: population.minimum_feasible,
          original,
          proposed: population.requested,
          change,
          changePercent,
          changeBarWidth: 0,
          planned: population.resolved,
          status: population.status,
        };
      },
    );

    const maxAbsPercentage = Math.max(
      ...rawRows
        .map((row) => Math.abs(row.changePercent ?? 0))
        .filter((value) => Number.isFinite(value)),
      1,
    );

    return rawRows.map((row) => ({
      ...row,
      changeBarWidth:
        row.changePercent === null
          ? 0
          : Math.min(
              100,
              (Math.abs(row.changePercent) / maxAbsPercentage) * 100,
            ),
    }));
  });
}
