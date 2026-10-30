import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkflowRowComponent } from '../../../../shared/components/workflow-row/workflow-row.component';

@Component({
  selector: 'app-generation-settings',
  standalone: true,
  imports: [WorkflowRowComponent, WorkspaceHeaderComponent, MetricGridComponent],
  templateUrl: './generation-settings.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationSettingsComponent {
  readonly generation = input<unknown>(null);

  readonly metrics = computed<MetricCardData[]>(() => {
    const generation = this.asRecord(this.generation());

    return [
      {
        label: 'Seed',
        value: this.displayValue(generation['seed']),
        description: 'Generation seed for reproducibility',
        icon: 'pin',
      },
      {
        label: 'Scenario',
        value: this.displayValue(generation['scenario']),
        description: 'Selected generation scenario',
        icon: 'tune',
      },
    ];
  });

  private asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {};
  }

  private displayValue(value: unknown): string {
    if (value === null || value === undefined || value === '') {
      return 'Not specified';
    }

    if (Array.isArray(value)) {
      return value.map((item) => this.displayValue(item)).join(', ');
    }

    if (typeof value === 'object') {
      return 'Configured';
    }

    return String(value);
  }
}
