import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';

import { GenerationQualityProfile } from '../../results.models';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';

@Component({
  selector: 'app-results-quality-summary',
  standalone: true,
  imports: [
    CommonModule,
    MetricGridComponent,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
  ],
  templateUrl: './results-quality-summary.component.html',
  styleUrl: './results-quality-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsQualitySummaryComponent {
  readonly quality = input<GenerationQualityProfile | null>(null);
  readonly viewDetails = output<void>();

  readonly metrics = (): MetricCardData[] => [
    {
      label: 'Population fidelity',
      value: `${this.populationFidelity().toFixed(1)}%`,
      description: 'Percentage of requested population achieved',
      icon: 'verified',
    },
    {
      label: 'Relationships analyzed',
      value: this.relationshipCount(),
      description: 'Relationships evaluated',
      icon: 'account_tree',
    },
    {
      label: 'Distributions analyzed',
      value: this.distributionCount(),
      description: 'Fields with distribution analysis',
      icon: 'pie_chart',
    },
    {
      label: 'Numeric fields analyzed',
      value: this.statisticalCount(),
      description: 'Numeric fields evaluated',
      icon: 'query_stats',
    },
    {
      label: 'Rows / second',
      value: Math.round(this.performance()).toLocaleString('en-US'),
      description: 'Generation throughput',
      icon: 'speed',
    },
    {
      label: 'Identity spaces analyzed',
      value: this.identityCount(),
      description: 'Entity identity spaces evaluated',
      icon: 'key',
    },
  ];

  populationFidelity(): number {
    return Number(
      (this.quality()?.population_fidelity as Record<string, unknown>)
        ?.['fidelity_rate'] ?? 0,
    ) * 100;
  }

  distributionCount(): number {
    return Number(
      (this.quality()?.distribution_fidelity as Record<string, unknown>)
        ?.['fields_analyzed'] ?? 0,
    );
  }

  relationshipCount(): number {
    return Number(
      (this.quality()?.relationship_fidelity as Record<string, unknown>)
        ?.['relationships_analyzed'] ?? 0,
    );
  }

  statisticalCount(): number {
    return Number(
      (this.quality()?.statistical_fidelity as Record<string, unknown>)
        ?.['numeric_fields_analyzed'] ?? 0,
    );
  }

  performance(): number {
    return Number(
      (this.quality()?.performance as Record<string, unknown>)
        ?.['rows_per_second'] ?? 0,
    );
  }

  identityCount(): number {
    const identity = this.quality()?.identity_space_utilization as
      | Record<string, unknown>
      | undefined;

    return Number(identity?.['entities_analyzed'] ?? 0);
  }
}
