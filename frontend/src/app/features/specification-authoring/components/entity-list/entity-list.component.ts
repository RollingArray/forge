import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkflowRowComponent } from '../../../../shared/components/workflow-row/workflow-row.component';

@Component({
  selector: 'app-entity-list',
  standalone: true,
  imports: [
    WorkspaceHeaderComponent,
    WorkflowRowComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-list.component.html',
  styleUrl: './entity-list.component.css',
})
export class EntityListComponent {
  readonly entities = input<unknown>([]);

  get entitiesValue(): unknown[] {
    return this.asArray(this.entities());
  }

  asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
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

  populationCount(entity: unknown): string {
    const population = this.asRecord(this.asRecord(entity)['population']);
    const count = population['count'];

    return count === null || count === undefined
      ? 'Not specified'
      : this.displayValue(count);
  }

  identityFields(entity: unknown): string {
    const identity = this.asRecord(this.asRecord(entity)['identity']);
    const fields = this.asArray(identity['fields']);

    return fields.length
      ? fields.map((field) => this.displayValue(field)).join(' + ')
      : 'Identity needs review';
  }

  fieldIdentityStrategy(field: unknown): string {
    const identity = this.asRecord(this.asRecord(field)['identity']);
    return this.displayValue(identity['strategy'] ?? null);
  }

  fieldGenerationSummary(field: unknown): string {
    const generation = this.asRecord(this.asRecord(field)['generation']);

    if (!Object.keys(generation).length) {
      return 'No field-level generation configuration';
    }

    const parts: string[] = [];

    for (const key of ['strategy', 'distribution', 'generator']) {
      const value = generation[key];

      if (value !== null && value !== undefined) {
        parts.push(`${this.humanize(key)}: ${this.displayValue(value)}`);
      }
    }

    const parameters = this.asRecord(generation['parameters']);

    for (const [key, value] of Object.entries(parameters)) {
      parts.push(`${this.humanize(key)}: ${this.displayValue(value)}`);
    }

    return parts.join(' · ') || 'Generation configured';
  }

  private humanize(value: string): string {
    return value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (character) => character.toUpperCase());
  }
}
