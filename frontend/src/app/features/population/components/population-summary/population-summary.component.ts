import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';

@Component({
  selector: 'app-population-summary',
  standalone: true,
  imports: [
    WorkspaceHeaderComponent,
    WorkspaceSectionComponent,
    MetricGridComponent,
  ],
  templateUrl: './population-summary.component.html',
  styleUrl: './population-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PopulationSummaryComponent {
  readonly targetRows = input<number | null>(null);
  readonly resolvedRows = input.required<number>();
  readonly gapRows = input<number | null>(null);
  readonly feasibleCount = input.required<number>();
  readonly entityCount = input.required<number>();
  readonly isCandidate = input(false);

  readonly metrics = () => [
    {
      label: 'Target Dataset Size',
      value: this.targetRows() ?? '—',
      description: 'User-defined dataset target',
      icon: 'database',
    },
    {
      label: this.isCandidate() ? 'Candidate Records' : 'Current Planned Records',
      value: this.resolvedRows(),
      description: this.isCandidate()
        ? 'Proposed population allocation'
        : 'Resolved population rows',
      icon: 'data_usage',
    },
    {
      label: 'Gap',
      value: this.gapRows() ?? '—',
      description: 'Difference from target',
      icon: 'compare_arrows',
    },
    {
      label: 'Feasibility',
      value: `${this.feasibleCount()} / ${this.entityCount()}`,
      description: this.isCandidate()
        ? 'Candidate entities feasible'
        : 'Entities currently feasible',
      icon: 'verified',
    },
  ] satisfies MetricCardData[];
}
