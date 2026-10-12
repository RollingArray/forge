import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { ForgeSpecification } from '../../../../core/interfaces/forge-specification.interface';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';

@Component({
  selector: 'app-model-studio-summary',
  standalone: true,
  imports: [
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    MetricGridComponent,
  ],
  templateUrl: './model-studio-summary.component.html',
  styleUrl: './model-studio-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelStudioSummaryComponent {
  readonly model = input.required<ForgeSpecification>();
  readonly addEntity = output<void>();

  readonly metrics = () => {
    const model = this.model();
    const entities = model.entities;
    const primaryKeyCount = entities.filter(
      (entity) => (entity.identity?.fields?.length ?? 0) > 0,
    ).length;
    const compositeKeyCount = entities.filter(
      (entity) => (entity.identity?.fields?.length ?? 0) > 1,
    ).length;

    return [
      {
        label: 'Entities',
        value: entities.length,
        description: 'Entities defined in the specification',
        icon: 'database',
      },
      {
        label: 'Fields',
        value: entities.reduce((total, entity) => total + entity.fields.length, 0),
        description: 'Fields defined across all entities',
        icon: 'view_column',
      },
      {
        label: 'Primary Keys',
        value: primaryKeyCount,
        description: 'Entities with a defined primary identity',
        icon: 'key',
      },
      {
        label: 'Composite Keys',
        value: compositeKeyCount,
        description: 'Identities containing multiple fields',
        icon: 'dataset',
      },
      {
        label: 'Foreign Keys',
        value: model.foreignKeys.length,
        description: 'Foreign key definitions in the specification',
        icon: 'link',
      },
      {
        label: 'Relationships',
        value: model.relationships.length,
        description: 'Relationships across entities',
        icon: 'account_tree',
      },
      {
        label: 'Constraints',
        value: model.constraints.length,
        description: 'Business constraints defined',
        icon: 'rule',
      },
      {
        label: 'Dependencies',
        value: model.dependencies.length,
        description: 'Dependencies defined in the specification',
        icon: 'hub',
      },
    ] satisfies MetricCardData[];
  };
}
