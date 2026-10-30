import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

interface DetailSectionDefinition {
  readonly key:
    | 'relationships'
    | 'foreign_keys'
    | 'constraints'
    | 'dependencies'
    | 'statistical_behavior'
    | 'scenarios';
  readonly title: string;
  readonly icon: string;
}

@Component({
  selector: 'app-detail-sections',
  standalone: true,
  templateUrl: './detail-sections.component.html',
  styleUrl: './detail-sections.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DetailSectionsComponent {
  readonly specification = input.required<unknown>();

  readonly sections: readonly DetailSectionDefinition[] = [
    { key: 'relationships', title: 'Relationships', icon: 'account_tree' },
    { key: 'foreign_keys', title: 'Foreign keys', icon: 'link' },
    { key: 'constraints', title: 'Constraints', icon: 'rule' },
    { key: 'dependencies', title: 'Dependencies', icon: 'conversion_path' },
    { key: 'statistical_behavior', title: 'Statistical behavior', icon: 'query_stats' },
    { key: 'scenarios', title: 'Scenarios', icon: 'tune' },
  ];

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
