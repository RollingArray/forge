import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { GenerationValidationSummary } from '../../../results/results.models';

@Component({
  selector: 'app-results-validation-summary',
  standalone: true,
  imports: [CommonModule, WorkspaceHeaderComponent, WorkspaceSectionComponent, MetricGridComponent],
  templateUrl: './results-validation-summary.component.html',
  styleUrl: './results-validation-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsValidationSummaryComponent {
  readonly validation = input.required<GenerationValidationSummary>();
  readonly modelName = input.required<string>();
  readonly modelDescription = input('');
  readonly jobId = input.required<string>();

  readonly metrics = (): MetricCardData[] => [
    {
      label: 'Entities checked',
      value: this.validation().entity_count,
      description: 'Entities included in validation',
      icon: 'dataset',
    },
    {
      label: 'Errors',
      value: this.validation().error_count,
      description: 'Validation errors detected',
      icon: 'error',
    },
    {
      label: 'Warnings',
      value: this.validation().warnings.length,
      description: 'Items requiring review',
      icon: 'warning',
    },
  ];
}
