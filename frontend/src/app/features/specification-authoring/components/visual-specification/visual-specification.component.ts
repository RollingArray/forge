import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { GenerationSettingsComponent } from '../generation-settings/generation-settings.component';
import { DetailSectionsComponent } from '../detail-sections/detail-sections.component';
import { EntityListComponent } from '../entity-list/entity-list.component';

@Component({
  selector: 'app-visual-specification',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    WorkspaceHeaderComponent,
    MetricGridComponent,
    GenerationSettingsComponent,
    DetailSectionsComponent,
    EntityListComponent,
  ],
  templateUrl: './visual-specification.component.html',
  styleUrl: './visual-specification.component.css',
})
export class VisualSpecificationComponent {
  readonly specification = input.required<unknown>();

  get specificationValue(): Record<string, unknown> {
    return this.asRecord(this.specification());
  }

  asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {};
  }

  asArray(value: unknown): unknown[] {
    return Array.isArray(value) ? value : [];
  }

  displayValue(value: unknown): string {
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
