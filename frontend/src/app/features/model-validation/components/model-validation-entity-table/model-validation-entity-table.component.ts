import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSimpleTableComponent } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkspaceSimpleTableColumn } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.models';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';

export interface ModelValidationEntityTableRow {
  name: string;
  checks: number;
  errors: number;
  warnings: number;
  status: 'valid' | 'warning' | 'error';
}

@Component({
  selector: 'app-model-validation-entity-table',
  standalone: true,
  imports: [
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceSimpleTableComponent,
    WorkspaceScrollAreaComponent,
  ],
  templateUrl: './model-validation-entity-table.component.html',
  styleUrl: './model-validation-entity-table.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelValidationEntityTableComponent {
  readonly entities = input.required<readonly ModelValidationEntityTableRow[]>();

  readonly searchTerm = signal('');

  readonly columns: readonly WorkspaceSimpleTableColumn<ModelValidationEntityTableRow>[] = [
    {
      key: 'name',
      label: 'Entity',
    },
    {
      key: 'checks',
      label: 'Checks',
      type: 'number',
    },
    {
      key: 'errors',
      label: 'Errors',
      type: 'error-count',
    },
    {
      key: 'warnings',
      label: 'Warnings',
      type: 'warning-count',
    },
    {
      key: 'status',
      label: 'Status',
      type: 'status',
    },
  ];

  readonly filteredEntities = computed(() => {
    const query = this.searchTerm().trim().toLowerCase();

    if (!query) {
      return this.entities();
    }

    return this.entities().filter((entity) => entity.name.toLowerCase().includes(query));
  });

  updateSearchTerm(value: string): void {
    this.searchTerm.set(value);
  }
}
