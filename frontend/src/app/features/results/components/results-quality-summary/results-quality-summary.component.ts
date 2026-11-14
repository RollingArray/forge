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
import {
  GenerationQualityMetricSummary,
  GenerationQualitySummary,
} from '../../results.models';
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
  readonly quality = input<GenerationQualitySummary | null>(null);
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
      value: this.measurementValue(this.quality()?.relationship_count),
      description: 'Relationships evaluated',
      icon: 'account_tree',
    },
    {
      label: 'Distributions analyzed',
      value: this.measurementValue(this.quality()?.distribution_count),
      description: 'Fields with distribution analysis',
      icon: 'pie_chart',
    },
    {
      label: 'Numeric fields analyzed',
      value: this.measurementValue(this.quality()?.statistical_count),
      description: 'Numeric fields evaluated',
      icon: 'query_stats',
    },
    {
      label: 'Rows / second',
      value: this.performance(),
      description: 'Generation throughput',
      icon: 'speed',
    },
    {
      label: 'Identity spaces analyzed',
      value: this.measurementValue(this.quality()?.identity_count),
      description: 'Entity identity spaces evaluated',
      icon: 'key',
    },
  ];

  private statusLabel(status: string | undefined): string | null {
    switch (status?.toUpperCase()) {
      case 'FAILED':
        return 'Failed';
      case 'UNAVAILABLE':
        return 'Not available';
      case 'INVALID_CONFIGURATION':
        return 'Invalid configuration';
      default:
        return null;
    }
  }

  private measurementValue(
    metric: GenerationQualityMetricSummary | undefined,
  ): number | string {
    const status = this.statusLabel(metric?.measurement_status);
    if (status) {
      return status;
    }

    const value = metric?.value;
    return typeof value === 'number' && Number.isFinite(value)
      ? value
      : 'Not available';
  }

  populationFidelity(): string {
    const metric = this.quality()?.population_fidelity;
    const status = this.statusLabel(metric?.measurement_status);

    if (status) {
      return status;
    }

    const value = metric?.value;
    return typeof value === 'number' && Number.isFinite(value)
      ? `${(value * 100).toFixed(1)}%`
      : 'Not available';
  }

  performance(): number | string {
    const value = this.measurementValue(this.quality()?.throughput);

    return typeof value === 'number'
      ? Math.round(value).toLocaleString('en-US')
      : value;
  }
}
