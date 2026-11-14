import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ForgeButtonComponent } from '../../../../shared/components/forge-button/forge-button.component';

import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { GenerationValidationSummaryResponse } from '../../results.models';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';

@Component({
  selector: 'app-results-validation',
  standalone: true,
  imports: [CommonModule, MetricGridComponent, WorkspaceSectionComponent, WorkspaceHeaderComponent, ForgeButtonComponent],
  templateUrl: './results-validation.component.html',
  styleUrl: './results-validation.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsValidationComponent {
  readonly validation = input<GenerationValidationSummaryResponse | null>(null);

  readonly viewDetails = output<void>();

  readonly metrics = (): MetricCardData[] => [
    {
      label: 'Rows validated',
      value: this.validation()?.rows_validated ?? 0,
      description: 'Generated rows checked',
      icon: 'database',
    },
    {
      label: 'Entities checked',
      value: this.validation()?.entities_checked ?? 0,
      description: 'Entities included in validation',
      icon: 'account_tree',
    },
    {
      label: 'Relationships checked',
      value: this.validation()?.relationships_checked ?? 0,
      description: 'Foreign-key relationships checked',
      icon: 'link',
    },
    {
      label: 'Constraints checked',
      value: this.validation()?.constraints_checked ?? 0,
      description: 'Business constraints checked',
      icon: 'rule',
    },
    {
      label: 'Errors',
      value: this.validation()?.error_count ?? 0,
      description: 'Validation errors found',
      icon: 'error',
    },
    {
      label: 'Warnings',
      value: this.validation()?.warning_count ?? 0,
      description: 'Validation warnings found',
      icon: 'warning',
    },
  ];

}
