import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import { DecimalPipe } from '@angular/common';

import {
  PopulationTableRow,
} from '../../models/population-plan.models';

interface PopulationOverviewItem {
  readonly entity: string;
  readonly resolved: number;
  readonly percentage: number;
}

@Component({
  selector: 'app-population-overview',
  standalone: true,
  imports: [DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './population-overview.component.html',
  styleUrl: './population-overview.component.css',
})
export class PopulationOverviewComponent {
  readonly rows =
    input<readonly PopulationTableRow[]>([]);

  readonly totalResolved = computed(() =>
    this.rows().reduce(
      (total, row) =>
        total + (row.resolved ?? 0),
      0,
    ),
  );

  readonly overview = computed<
    readonly PopulationOverviewItem[]
  >(() => {
    const total = this.totalResolved();

    return [...this.rows()]
      .filter(row => (row.resolved ?? 0) > 0)
      .map(row => {
        const resolved = row.resolved ?? 0;

        return {
          entity: row.entity,
          resolved,
          percentage:
            total > 0
              ? (resolved / total) * 100
              : 0,
        };
      })
      .sort(
        (a, b) =>
          b.resolved - a.resolved,
      );
  });

  readonly largestEntity = computed(
    () => this.overview()[0] ?? null,
  );
}
