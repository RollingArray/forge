import { DecimalPipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {
  PopulationEntityPlan,
  PopulationPlan,
} from '../../models/population.models';

interface PopulationTableRow {
  entity: string;
  plan: PopulationEntityPlan;
  original: number | null;
  change: number | null;
  changePercent: number | null;
  changeBarWidth: number;
}

@Component({
  selector: 'app-entity-population-table',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './entity-population-table.component.html',
  styleUrl: './entity-population-table.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityPopulationTableComponent {
  readonly plan = input.required<PopulationPlan>();
  readonly originalPlan = input.required<PopulationPlan>();

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
          plan: population,
          original,
          change,
          changePercent,
          changeBarWidth: 0,
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
