import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { GenerationValidationSummary } from '../../results.models';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';

@Component({
  selector: 'app-results-validation',
  standalone: true,
  imports: [
    CommonModule,
    MetricGridComponent,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
  ],
  templateUrl: './results-validation.component.html',
  styleUrl: './results-validation.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsValidationComponent {
  readonly validation = input<GenerationValidationSummary | null>(null);

  readonly metrics = (): MetricCardData[] => [
    {
      label: 'Rows validated',
      value: this.validation()?.generated_rows ?? 0,
      description: 'Generated rows checked',
      icon: 'database',
    },
    {
      label: 'Entities checked',
      value: this.validation()?.entity_count ?? 0,
      description: 'Entities included in validation',
      icon: 'account_tree',
    },
    {
      label: 'Relationships checked',
      value: this.foreignKeyCount(),
      description: 'Foreign-key relationships checked',
      icon: 'link',
    },
    {
      label: 'Constraints checked',
      value: this.constraintCount(),
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
      value: this.validation()?.warnings?.length ?? 0,
      description: 'Validation warnings found',
      icon: 'warning',
    },
  ];

  foreignKeyCount(): number {
    const evidence = this.validation()?.evidence as Record<string, any> | undefined;
    return evidence?.['foreign_keys']?.['relationships_checked'] ?? 0;
  }

  constraintCount(): number {
    const evidence = this.validation()?.evidence as Record<string, any> | undefined;
    return evidence?.['constraints']?.['constraints_checked'] ?? 0;
  }
}
