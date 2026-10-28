import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  signal,
} from '@angular/core';

import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSimpleTableComponent } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkflowRowComponent } from '../../../../shared/components/workflow-row/workflow-row.component';
import { WorkspaceSimpleTableColumn } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.models';

interface DistributionCategoryRow {
  key: string;
  category: string;
  observedCount: number;
  observedProbability: string;
  expectedProbability: string;
  absoluteDeviation: string;
}

interface DistributionFieldRow {
  key: string;
  entity: string;
  field: string;
  rowsObserved: number;
  rowsTotal: number;
  categories: string;
  categoryCoverage: string;
  missingCount: number;
  maximumDeviation: string;
}

interface DistributionFieldRecord {
  key: string;
  entity: string;
  field: string;
  rowsObserved: number;
  rowsTotal: number;
  missingCount: number;
  observedCategoryCount: number;
  declaredCategoryCount: number;
  categoryCoverage: number;
  maximumDeviation: number;
  categories: DistributionCategoryRow[];
}

@Component({
  selector: 'app-distribution-fidelity-visualization',
  standalone: true,
  imports: [MetricGridComponent, WorkspaceHeaderComponent, WorkspaceSimpleTableComponent, WorkflowRowComponent],
  templateUrl: './distribution-fidelity-visualization.component.html',
  styleUrl: './distribution-fidelity-visualization.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DistributionFidelityVisualizationComponent {
  readonly profile = input.required<Record<string, unknown>>();
  readonly selectedFieldKey = signal<string | null>(null);

  private readonly fieldRecords = computed<DistributionFieldRecord[]>(() => {
    const rawFields = this.profile()['fields'];

    // The backend currently returns a dictionary keyed by Entity.Field.
    const entries: Array<[string, unknown]> = Array.isArray(rawFields)
      ? rawFields.map((value: unknown, index: number) => [String(index), value])
      : Object.entries(this.asRecord(rawFields));

    return entries.map(([entryKey, raw], index) => {
      const field = this.asRecord(raw);
      const rawValues = this.asRecord(field['values']);
      const categories = Object.entries(rawValues).map(([name, rawValue]) => {
        const value = this.asRecord(rawValue);
        return {
          key: name,
          category: name,
          observedCount: this.number(value['observed_count']),
          observedProbability: this.formatProbability(value['observed_probability']),
          expectedProbability: this.formatProbability(value['expected_probability']),
          absoluteDeviation: this.formatProbability(
            value['absolute_probability_difference'],
          ),
        };
      });

      const [keyEntity, keyField] = entryKey.includes('.')
        ? [
            entryKey.slice(0, entryKey.lastIndexOf('.')),
            entryKey.slice(entryKey.lastIndexOf('.') + 1),
          ]
        : ['', ''];

      return {
        key: entryKey || String(index),
        entity: this.string(field['entity'], keyEntity || '—'),
        field: this.string(field['field'], keyField || `Field ${index + 1}`),
        rowsObserved: this.number(field['rows_observed']),
        rowsTotal: this.number(field['rows_total']),
        missingCount: this.number(field['missing_count']),
        observedCategoryCount: this.number(field['observed_category_count']),
        declaredCategoryCount: this.number(field['declared_category_count']),
        categoryCoverage: this.number(field['category_coverage']),
        maximumDeviation: this.number(
          field['maximum_absolute_probability_difference'],
        ),
        categories,
      };
    });
  });

  readonly fieldRows = computed<DistributionFieldRow[]>(() =>
    this.fieldRecords().map((field) => ({
      key: field.key,
      entity: field.entity,
      field: field.field,
      rowsObserved: field.rowsObserved,
      rowsTotal: field.rowsTotal,
      categories: `${field.observedCategoryCount} / ${field.declaredCategoryCount}`,
      categoryCoverage: this.formatPercent(field.categoryCoverage),
      missingCount: field.missingCount,
      maximumDeviation: this.formatProbability(field.maximumDeviation),
    })),
  );

  readonly metrics = computed<MetricCardData[]>(() => {
    const records = this.fieldRecords();
    const averageCoverage = records.length
      ? records.reduce((sum, field) => sum + field.categoryCoverage, 0) / records.length
      : null;

    return [
      {
        label: 'Fields analyzed',
        value: this.number(this.profile()['fields_analyzed']),
        description: 'Categorical fields with declared distributions',
        icon: 'analytics',
      },
      {
        label: 'Declared categories',
        value: records.reduce((sum, field) => sum + field.declaredCategoryCount, 0),
        description: 'Configured categories across analyzed fields',
        icon: 'category',
      },
      {
        label: 'Average category coverage',
        value: averageCoverage === null ? 'Not available' : this.formatPercent(averageCoverage),
        description: 'Mean category coverage across analyzed fields',
        icon: 'pie_chart',
      },
      {
        label: 'Fields with missing values',
        value: records.filter((field) => field.missingCount > 0).length,
        description: 'Analyzed fields with one or more missing values',
        icon: 'rule',
      },
    ];
  });

  readonly fieldColumns: readonly WorkspaceSimpleTableColumn<DistributionFieldRow>[] = [
    { key: 'entity', label: 'Entity', width: 'minmax(130px, 1fr)' },
    { key: 'field', label: 'Field', width: 'minmax(130px, 1fr)' },
    { key: 'rowsObserved', label: 'Rows observed', type: 'number', width: '115px', align: 'right' },
    { key: 'categories', label: 'Categories observed / declared', width: '170px', align: 'right' },
    { key: 'categoryCoverage', label: 'Category coverage', width: '140px', align: 'right' },
    { key: 'missingCount', label: 'Missing', type: 'number', width: '90px', align: 'right' },
    { key: 'maximumDeviation', label: 'Max. probability deviation', width: '175px', align: 'right' },
  ];

  readonly categoryColumns: readonly WorkspaceSimpleTableColumn<DistributionCategoryRow>[] = [
    { key: 'category', label: 'Category', width: 'minmax(140px, 1fr)' },
    { key: 'observedCount', label: 'Observed count', type: 'number', width: '130px', align: 'right' },
    { key: 'observedProbability', label: 'Observed probability', width: '155px', align: 'right' },
    { key: 'expectedProbability', label: 'Expected probability', width: '155px', align: 'right' },
    { key: 'absoluteDeviation', label: 'Absolute deviation', width: '145px', align: 'right' },
  ];

  readonly selectedField = computed(() => {
    const key = this.selectedFieldKey();
    return key === null
      ? null
      : this.fieldRecords().find((field) => field.key === key) ?? null;
  });

  readonly selectedCategoryRows = computed(
    () => this.selectedField()?.categories ?? [],
  );

  readonly selectedFieldSummary = computed(() => {
    const field = this.selectedField();
    return field ? `${field.entity} · ${field.field}` : '';
  });

  readonly selectedCategoryCount = computed(
    () => `${this.selectedCategoryRows().length} categories`,
  );

  selectField(row: DistributionFieldRow): void {
    this.selectedFieldKey.set(row.key);
  }

  asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {};
  }

  private number(value: unknown): number {
    if (value === null || value === undefined || value === '') return 0;
    const result = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(result) ? result : 0;
  }

  private string(value: unknown, fallback: string): string {
    return typeof value === 'string' && value.length ? value : fallback;
  }

  private formatPercent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }

  private formatProbability(value: unknown): string {
    return `${(this.number(value) * 100).toFixed(2)}%`;
  }
}
