import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';

@Component({
  selector: 'app-visual-specification',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [WorkspaceHeaderComponent, MetricGridComponent, WorkspaceSectionComponent],
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

  recordTitle(item: unknown, fallback: string): string {
    const record = this.asRecord(item);
    for (const key of ['name', 'title', 'entity', 'field', 'id']) {
      const value = record[key];
      if (typeof value === 'string' && value.trim()) {
        return value;
      }
    }
    return fallback;
  }

  recordSummary(item: unknown): string {
    const record = this.asRecord(item);

    if ('source' in record && 'target' in record) {
      const type = record['type'];
      const participation = [
        record['source_participation'],
        record['target_participation'],
      ].filter((value) => value !== undefined && value !== null);

      return [
        `${this.referenceText(record['source'])} → ${this.referenceText(record['target'])}`,
        type ? this.displayValue(type) : '',
        participation.length
          ? participation.map((value) => this.displayValue(value)).join(' / ')
          : '',
      ].filter(Boolean).join(' · ');
    }

    if ('operator' in record && 'field' in record) {
      const left = [
        record['entity'] ? this.displayValue(record['entity']) : '',
        this.displayValue(record['field']),
      ].filter(Boolean).join('.');
      return `${left} ${this.displayValue(record['operator'])} ${this.displayValue(record['value'])}`;
    }

    const ignored = new Set(['name', 'title', 'id']);
    const parts = Object.entries(record)
      .filter(([key, value]) =>
        !ignored.has(key) &&
        value !== null &&
        value !== undefined &&
        typeof value !== 'object',
      )
      .map(([key, value]) => `${this.humanize(key)}: ${this.displayValue(value)}`);

    return parts.join(' · ') || 'Details available for review';
  }

  referenceText(value: unknown): string {
    if (typeof value === 'string') {
      return value;
    }

    const record = this.asRecord(value);
    const entity = this.displayValue(record['entity']);
    const fields = this.asArray(record['fields'])
      .map((field) => this.displayValue(field))
      .join(' + ');

    return fields ? `${entity}.${fields}` : entity;
  }

  humanize(value: string): string {
    return value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (character) => character.toUpperCase());
  }
}
