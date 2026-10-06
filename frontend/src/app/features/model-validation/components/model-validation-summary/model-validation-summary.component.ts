import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { ForgeSpecification } from '../../../../core/interfaces/forge-specification.interface';
import { SpecificationValidationResult } from '../../../../core/interfaces/specification-validation.interface';

import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { StatusCardComponent } from '../../../../shared/components/status-card/status-card.component';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';

@Component({
  selector: 'app-model-validation-summary',
  standalone: true,
  imports: [
    WorkspaceHeaderComponent,
    WorkspaceSectionComponent,
    MetricGridComponent,
    StatusCardComponent,
  ],
  templateUrl: './model-validation-summary.component.html',
  styleUrl: './model-validation-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelValidationSummaryComponent {
  readonly model = input.required<ForgeSpecification>();
  readonly validation = input.required<SpecificationValidationResult>();

  readonly primaryKeyCount = input.required<number>();
  readonly foreignKeyCount = input.required<number>();
  readonly compositeKeyCount = input.required<number>();

  readonly metrics = () => [
    {
      label: 'Entities',
      value: this.model().entities.length,
      description: 'Entities defined in the specification',
      icon: 'database',
    },
    {
      label: 'Relationships',
      value: this.model().relationships.length,
      description: 'Relationships across entities',
      icon: 'account_tree',
    },
    {
      label: 'Constraints',
      value: this.model().constraints.length,
      description: 'Business constraints defined',
      icon: 'rule',
    },
    {
      label: 'Primary Keys',
      value: this.primaryKeyCount(),
      description: 'Entity identity definitions',
      icon: 'key',
    },
    {
      label: 'Foreign Keys',
      value: this.foreignKeyCount(),
      description: 'Referential integrity definitions',
      icon: 'link',
    },
    {
      label: 'Composite Keys',
      value: this.compositeKeyCount(),
      description: 'Multi-field identity definitions',
      icon: 'key_vertical',
    },
  ] satisfies MetricCardData[];
}
