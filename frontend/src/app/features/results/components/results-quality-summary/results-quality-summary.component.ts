import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ForgeButtonComponent } from '../../../../shared/components/forge-button/forge-button.component';
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
    ForgeButtonComponent,
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
      value: this.populationFidelity(),
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
      value: typeof this.performance() === 'number'
        ? Math.round(this.performance() as number).toLocaleString('en-US')
        : this.performance(),
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

  private measurementValue(
    dimension: keyof GenerationQualityProfile,
    metric: string,
  ): number | string {
    const profile = this.quality()?.[dimension] as
      | Record<string, unknown>
      | undefined;

    const status = profile?.['measurement_status'];

    if (status === 'FAILED') return 'Failed';
    if (status === 'UNAVAILABLE') return 'Not available';
    if (status === 'INVALID_CONFIGURATION') return 'Invalid configuration';

    const value = profile?.[metric];

    if (value === null || value === undefined || value === '') {
      return 'Not available';
    }

    const number = Number(value);
    return Number.isFinite(number) ? number : 'Not available';
  }

  populationFidelity(): string {
    const profile = this.quality()?.population_fidelity;
    const status = profile?.['measurement_status'];

    if (status === 'FAILED') return 'Failed';
    if (status === 'UNAVAILABLE') return 'Not available';
    if (status === 'INVALID_CONFIGURATION') return 'Invalid configuration';

    const value = profile?.['fidelity_rate'];

    if (value === null || value === undefined || value === '') {
      return 'Not available';
    }

    const fidelity = Number(value);

    return Number.isFinite(fidelity)
      ? `${(fidelity * 100).toFixed(1)}%`
      : 'Not available';
  }

  distributionCount(): number | string {
    return this.measurementValue(
      'distribution_fidelity',
      'fields_analyzed',
    );
  }

  relationshipCount(): number | string {
    return this.measurementValue(
      'relationship_fidelity',
      'relationships_analyzed',
    );
  }

  statisticalCount(): number | string {
    return this.measurementValue(
      'statistical_fidelity',
      'numeric_fields_analyzed',
    );
  }

  performance(): number | string {
    return this.measurementValue(
      'performance',
      'rows_per_second',
    );
  }

  identityCount(): number | string {
    return this.measurementValue(
      'identity_space_utilization',
      'entities_analyzed',
    );
  }
}
