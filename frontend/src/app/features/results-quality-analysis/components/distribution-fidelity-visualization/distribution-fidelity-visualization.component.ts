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
  measurementStatus: string;
  rowsObserved: string;
  categories: string;
  categoryCoverage: string;
  missingCount: string;
  maximumDeviation: string;
}

interface DistributionFieldRecord {
  key: string;
  entity: string;
  field: string;
  measurementStatus: string;
  invalidReason: string | null;
  rowsObserved: number | null;
  missingCount: number | null;
  observedCategoryCount: number;
  declaredCategoryCount: number;
  categoryCoverage: number | null;
  maximumDeviation: number | null;
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

  readonly measurementStatus = computed(() =>
    this.string(this.profile()['measurement_status'], 'UNKNOWN'),
  );

  readonly measurementMessage = computed(() => {
    const status = this.measurementStatus();

    if (status === 'FAILED') {
      return 'Distribution fidelity measurement failed. Other generation results remain available.';
    }

    if (status === 'UNAVAILABLE') {
      return 'No usable distribution measurements were recorded.';
    }

    if (status === 'INVALID_CONFIGURATION') {
      return this.string(
        this.profile()['invalid_reason'],
        'The distribution measurement configuration is invalid.',
      );
    }

    return '';
  });

  readonly measurementFailed = computed(() =>
    ['FAILED', 'UNAVAILABLE', 'INVALID_CONFIGURATION'].includes(
      this.measurementStatus(),
    ),
  );

  private readonly fieldRecords = computed<DistributionFieldRecord[]>(() => {
    const rawFields = this.profile()['fields'];

    const entries: Array<[string, unknown]> = Array.isArray(rawFields)
      ? rawFields.map((value: unknown, index: number) => [String(index), value])
      : Object.entries(this.asRecord(rawFields));

    return entries.map(([entryKey, raw], index) => {
      const field = this.asRecord(raw);
      const rawValues = this.asRecord(field['values']);
      const rowsObserved = this.nullableNumber(field['rows_observed']);

      const categories: DistributionCategoryRow[] = Object.entries(rawValues)
        .map(([name, rawValue]) => {
          const value = this.asRecord(rawValue);
          return {
            key: name,
            category: name,
            observedCount: this.number(value['observed_count']),
            observedProbability: this.formatNullableProbability(
              value['observed_probability'],
            ),
            expectedProbability: this.formatNullableProbability(
              value['expected_probability'],
            ),
            absoluteDeviation: this.formatNullableProbability(
              value['absolute_probability_difference'],
            ),
          };
        });

      const unexpectedCategories = this.asRecord(
        field['unexpected_categories'],
      );

      for (const [name, rawCount] of Object.entries(unexpectedCategories)) {
        const count = this.number(rawCount);
        categories.push({
          key: `unexpected:${name}`,
          category: `${name} (unexpected)`,
          observedCount: count,
          observedProbability: rowsObserved !== null && rowsObserved > 0
            ? this.formatNullableProbability(count / rowsObserved)
            : 'Not available',
          expectedProbability: 'Not declared',
          absoluteDeviation: 'Not applicable',
        });
      }

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
        measurementStatus: this.string(
          field['measurement_status'],
          'UNKNOWN',
        ),
        invalidReason: typeof field['invalid_reason'] === 'string'
          ? field['invalid_reason']
          : null,
        rowsObserved,
        missingCount: this.nullableNumber(field['missing_count']),
        observedCategoryCount: this.number(field['observed_category_count']),
        declaredCategoryCount: this.number(field['declared_category_count']),
        categoryCoverage: this.nullableNumber(field['category_coverage']),
        maximumDeviation: this.nullableNumber(
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
      measurementStatus: field.measurementStatus,
      rowsObserved: field.rowsObserved === null
        ? 'Not available'
        : String(field.rowsObserved),
      categories: `${field.observedCategoryCount} / ${field.declaredCategoryCount}`,
      categoryCoverage: this.formatPercent(field.categoryCoverage),
      missingCount: field.missingCount === null
        ? 'Not available'
        : String(field.missingCount),
      maximumDeviation: this.formatNullableProbability(field.maximumDeviation),
    })),
  );

  readonly metrics = computed<MetricCardData[]>(() => {
    const records = this.fieldRecords();
    const measuredCoverage = records
      .filter(
        (field) =>
          field.measurementStatus === 'AVAILABLE' &&
          field.categoryCoverage !== null,
      )
      .map((field) => field.categoryCoverage as number);
    const averageCoverage = measuredCoverage.length
      ? measuredCoverage.reduce((sum, value) => sum + value, 0) /
        measuredCoverage.length
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
        value: records.filter(
          (field) => field.missingCount !== null && field.missingCount > 0,
        ).length,
        description: 'Analyzed fields with one or more missing values',
        icon: 'rule',
      },
    ];
  });

  readonly fieldColumns: readonly WorkspaceSimpleTableColumn<DistributionFieldRow>[] = [
    { key: 'entity', label: 'Entity', width: 'minmax(130px, 1fr)' },
    { key: 'field', label: 'Field', width: 'minmax(130px, 1fr)' },
    { key: 'measurementStatus', label: 'Measurement status', width: '165px' },
    { key: 'rowsObserved', label: 'Rows observed', width: '125px', align: 'right' },
    { key: 'categories', label: 'Categories observed / declared', width: '170px', align: 'right' },
    { key: 'categoryCoverage', label: 'Category coverage', width: '140px', align: 'right' },
    { key: 'missingCount', label: 'Missing', width: '120px', align: 'right' },
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

  private nullableNumber(value: unknown): number | null {
    if (value === null || value === undefined || value === '') return null;
    const result = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(result) ? result : null;
  }

  private formatPercent(value: number | null): string {
    return value === null
      ? 'Not available'
      : `${(value * 100).toFixed(1)}%`;
  }

  private formatNullableProbability(value: unknown): string {
    const result = this.nullableNumber(value);
    return result === null
      ? 'Not available'
      : `${(result * 100).toFixed(2)}%`;
  }
}
