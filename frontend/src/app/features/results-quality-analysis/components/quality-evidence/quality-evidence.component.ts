import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { ContentGridComponent } from '../../../../shared/components/content-grid/content-grid.component';
import { ContentCardComponent } from '../../../../shared/components/content-card/content-card.component';
import { WorkspaceSimpleTableComponent } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkspaceSimpleTableColumn } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.models';
import { QualityEvidenceSection } from '../../../../core/interfaces/quality-evidence-section.interface';
import { PopulationFidelityVisualizationComponent } from '../population-fidelity-visualization/population-fidelity-visualization.component';
import { DistributionFidelityVisualizationComponent } from '../distribution-fidelity-visualization/distribution-fidelity-visualization.component';

interface RelationshipRow {
  key: string;
  relationship: string;
  source: string;
  target: string;
  relationshipType: string;
  parentRows: string;
  childRows: string;
  matchedRows: string;
  orphanRows: string;
  missingReferences: string;
  parentParticipation: string;
  status: string;
  note: string;
}

interface IdentityRow {
  entity: string;
  identityFields: string;
  capacity: string;
  uniqueIdentities: string;
  utilization: string;
  capacityBasis: string;
  status: string;
}

interface StatisticalRow {
  key: string;
  entity: string;
  field: string;
  rowsMeasured: string;
  minimum: string;
  maximum: string;
  mean: string;
  standardDeviation: string;
  median: string;
  percentile95: string;
  status: string;
}

interface PerformanceRow {
  key: string;
  generatedRows: string;
  elapsedSeconds: string;
  rowsPerSecond: string;
  status: string;
}

interface DetailRow {
  label: string;
  value: string;
}

@Component({
  selector: 'app-quality-evidence',
  standalone: true,
  imports: [
    WorkspaceHeaderComponent,
    WorkspaceScrollAreaComponent,
    WorkspaceSectionComponent,
    ContentGridComponent,
    ContentCardComponent,
    WorkspaceSimpleTableComponent,
    PopulationFidelityVisualizationComponent,
    DistributionFidelityVisualizationComponent,
  ],
  templateUrl: './quality-evidence.component.html',
  styleUrl: './quality-evidence.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QualityEvidenceComponent {
  readonly sections = input.required<readonly QualityEvidenceSection[]>();
  readonly populationProfile = input.required<Record<string, unknown>>();
  readonly distributionProfile = input.required<Record<string, unknown>>();

  readonly sectionIcons: Record<string, string> = {
    'Population Fidelity': 'database',
    'Distribution Fidelity': 'chart_data',
    'Relationship Fidelity': 'account_tree',
    'Identity Space Utilization': 'fingerprint',
    'Statistical Fidelity': 'scatter_plot',
    Performance: 'speed',
    Validation: 'verified_user',
  };

  readonly relationshipColumns: readonly WorkspaceSimpleTableColumn<RelationshipRow>[] = [
    { key: 'relationship', label: 'Relationship', width: 'minmax(150px, 1fr)' },
    { key: 'source', label: 'Parent entity', width: 'minmax(170px, 1.3fr)' },
    { key: 'target', label: 'Child entity', width: 'minmax(170px, 1.3fr)' },
    { key: 'relationshipType', label: 'Type', width: '130px' },
    { key: 'parentRows', label: 'Parent rows', align: 'right' },
    { key: 'childRows', label: 'Child rows', align: 'right' },
    { key: 'matchedRows', label: 'Matched references', align: 'right' },
    { key: 'orphanRows', label: 'Orphan references', type: 'error-count', align: 'right' },
    { key: 'missingReferences', label: 'Missing references', type: 'warning-count', align: 'right' },
    { key: 'parentParticipation', label: 'Parent participation', align: 'right' },
    { key: 'status', label: 'Measurement status', type: 'status', width: '145px' },
  ];

  readonly identityColumns: readonly WorkspaceSimpleTableColumn<IdentityRow>[] = [
    { key: 'entity', label: 'Entity', width: 'minmax(140px, 1fr)' },
    { key: 'identityFields', label: 'Identity fields', width: 'minmax(160px, 1.2fr)' },
    { key: 'capacity', label: 'Identity-space capacity', align: 'right' },
    { key: 'uniqueIdentities', label: 'Unique identities generated', align: 'right' },
    { key: 'utilization', label: 'Space utilization', align: 'right' },
    { key: 'capacityBasis', label: 'Capacity basis', width: 'minmax(180px, 1.4fr)' },
    { key: 'status', label: 'Capacity status', type: 'status', width: '145px' },
  ];

  readonly statisticalColumns: readonly WorkspaceSimpleTableColumn<StatisticalRow>[] = [
    { key: 'entity', label: 'Entity', width: 'minmax(130px, 1fr)' },
    { key: 'field', label: 'Numeric field', width: 'minmax(140px, 1fr)' },
    { key: 'rowsMeasured', label: 'Values measured', align: 'right' },
    { key: 'minimum', label: 'Minimum', align: 'right' },
    { key: 'maximum', label: 'Maximum', align: 'right' },
    { key: 'mean', label: 'Mean', align: 'right' },
    { key: 'standardDeviation', label: 'Std. deviation', align: 'right' },
    { key: 'median', label: 'P50', align: 'right' },
    { key: 'percentile95', label: 'P95', align: 'right' },
    { key: 'status', label: 'Measurement status', type: 'status', width: '135px' },
  ];

  readonly performanceColumns: readonly WorkspaceSimpleTableColumn<PerformanceRow>[] = [
    { key: 'generatedRows', label: 'Generated rows', align: 'right' },
    { key: 'elapsedSeconds', label: 'Elapsed time', align: 'right' },
    { key: 'rowsPerSecond', label: 'Throughput (rows/sec)', align: 'right' },
    { key: 'status', label: 'Measurement status', type: 'status', width: '145px' },
  ];

  readonly detailColumns: readonly WorkspaceSimpleTableColumn<DetailRow>[] = [
    { key: 'label', label: 'Evidence item', width: 'minmax(200px, 1fr)' },
    { key: 'value', label: 'Recorded value', width: 'minmax(200px, 1.5fr)' },
  ];

  iconFor(title: string): string {
    return this.sectionIcons[title] ?? 'analytics';
  }

  hasUnavailableMeasurement(section: QualityEvidenceSection): boolean {
    return ['FAILED', 'UNAVAILABLE', 'INVALID_CONFIGURATION'].includes(
      this.stringValue(section.evidence['measurement_status'], ''),
    );
  }

  measurementMessage(section: QualityEvidenceSection): string {
    const evidence = section.evidence;
    const status = this.stringValue(evidence['measurement_status'], '');

    if (status === 'FAILED') {
      return 'This quality measurement failed. Other generation results remain available.';
    }

    if (status === 'UNAVAILABLE') {
      return 'No usable measurements were recorded for this quality dimension.';
    }

    if (status === 'INVALID_CONFIGURATION') {
      return this.stringValue(
        evidence['invalid_reason'],
        'The measurement configuration is invalid.',
      );
    }

    return '';
  }

  relationshipRows(section: QualityEvidenceSection): RelationshipRow[] {
    const groups = this.asRecord(section.evidence['relationships']);

    return Object.entries(groups).map(([key, raw]) => {
      const group = this.asRecord(raw);
      const status = this.stringValue(group['measurement_status'], 'unknown');

      return {
        key,
        relationship: this.titleFromKey(key),
        source: this.entityFields(
          group['parent_entity'] ?? group['source_entity'],
          group['parent_fields'] ?? group['source_fields'],
        ),
        target: this.entityFields(
          group['child_entity'] ?? group['target_entity'],
          group['child_fields'] ?? group['target_fields'],
        ),
        relationshipType: this.stringValue(
          group['relationship_type'],
          'Not specified',
        ).replaceAll('_', ' '),
        parentRows: this.displayNumber(group['parent_rows_checked']),
        childRows: this.displayNumber(group['child_rows_checked']),
        matchedRows: this.displayNumber(group['matched_child_rows']),
        orphanRows: this.displayNumber(group['orphan_child_rows']),
        missingReferences: this.displayNumber(
          this.sumNullable(
            group['null_reference_rows'],
            group['partial_null_reference_rows'],
          ),
        ),
        parentParticipation: this.formatPercent(group['parent_participation_rate']),
        status: this.relationshipStatus(status),
        note: this.stringValue(group['measurement_note'], ''),
      };
    });
  }

  identityRows(section: QualityEvidenceSection): IdentityRow[] {
    const entities = this.asRecord(section.evidence['entities']);

    return Object.entries(entities).map(([entity, raw]) => {
      const record = this.asRecord(raw);
      const determinable = record['capacity_determinable'] === true;
      const sources = this.stringList(record['dimension_sources']);

      return {
        entity,
        identityFields: this.stringList(record['identity_fields']).join(', ') || 'Not available',
        capacity: determinable
          ? this.displayNumber(record['identity_space_capacity'])
          : 'Not determinable',
        uniqueIdentities: this.displayNumber(record['generated_unique_identities']),
        utilization: determinable
          ? this.formatPercent(record['utilization_rate'])
          : 'Not available',
        capacityBasis: sources.length
          ? sources.join(', ')
          : 'Insufficient finite domains or mapped parent keys',
        status: determinable ? 'DETERMINED' : 'NOT DETERMINABLE',
      };
    });
  }

  statisticalRows(section: QualityEvidenceSection): StatisticalRow[] {
    const fields = this.asRecord(section.evidence['fields']);

    return Object.entries(fields).map(([key, raw]) => {
      const field = this.asRecord(raw);
      const statistics = this.asRecord(field['statistics']);

      return {
        key,
        entity: this.stringValue(field['entity'], 'Unknown entity'),
        field: this.stringValue(field['field'], key),
        rowsMeasured: this.displayNumber(statistics['count']),
        minimum: this.displayNumber(statistics['minimum']),
        maximum: this.displayNumber(statistics['maximum']),
        mean: this.displayNumber(statistics['mean']),
        standardDeviation: this.displayNumber(statistics['standard_deviation']),
        median: this.displayNumber(statistics['p50']),
        percentile95: this.displayNumber(statistics['p95']),
        status: Object.keys(statistics).length ? 'MEASURED' : 'UNAVAILABLE',
      };
    });
  }

  performanceRows(section: QualityEvidenceSection): PerformanceRow[] {
    const evidence = section.evidence;
    const available = evidence['available'] === true;

    return [{
      key: 'performance',
      generatedRows: available
        ? this.displayNumber(evidence['total_generated_rows'])
        : 'Not available',
      elapsedSeconds: available
        ? this.withUnit(evidence['elapsed_seconds'], 's')
        : 'Not available',
      rowsPerSecond: available
        ? this.displayNumber(evidence['rows_per_second'])
        : 'Not available',
      status: available ? 'AVAILABLE' : 'UNAVAILABLE',
    }];
  }

  detailRows(section: QualityEvidenceSection): DetailRow[] {
    return section.items.map((item) => ({
      label: item.label,
      value: item.value,
    }));
  }

  recordCount(section: QualityEvidenceSection): number {
    switch (section.key) {
      case 'relationship_fidelity':
        return Object.keys(this.asRecord(section.evidence['relationships'])).length;
      case 'identity_space_utilization':
        return Object.keys(this.asRecord(section.evidence['entities'])).length;
      case 'statistical_fidelity':
        return Object.keys(this.asRecord(section.evidence['fields'])).length;
      case 'performance':
        return 1;
      default:
        return section.items.length;
    }
  }

  private asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {};
  }

  private stringValue(value: unknown, fallback: string): string {
    return typeof value === 'string' && value.trim() ? value : fallback;
  }

  private stringList(value: unknown): string[] {
    return Array.isArray(value)
      ? value.filter((item): item is string => typeof item === 'string')
      : [];
  }

  private entityFields(entity: unknown, fields: unknown): string {
    const name = this.stringValue(entity, 'Unknown entity');
    const fieldNames = this.stringList(fields);
    return fieldNames.length ? `${name} · ${fieldNames.join(', ')}` : name;
  }

  private numberValue(value: unknown): number | null {
    if (value === null || value === undefined || value === '') return null;
    const result = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(result) ? result : null;
  }

  private displayNumber(value: unknown): string {
    const number = this.numberValue(value);
    if (number === null) return 'Not available';

    return number.toLocaleString('en-US', {
      maximumFractionDigits: 4,
    });
  }

  private formatPercent(value: unknown): string {
    const number = this.numberValue(value);
    return number === null
      ? 'Not available'
      : `${(number * 100).toFixed(2)}%`;
  }

  private withUnit(value: unknown, unit: string): string {
    const number = this.numberValue(value);
    return number === null ? 'Not available' : `${number.toFixed(3)} ${unit}`;
  }

  private sumNullable(first: unknown, second: unknown): number | null {
    const left = this.numberValue(first);
    const right = this.numberValue(second);
    return left === null && right === null
      ? null
      : (left ?? 0) + (right ?? 0);
  }

  private relationshipStatus(status: string): string {
    switch (status) {
      case 'measured':
        return 'MEASURED';
      case 'inconclusive':
        return 'INCONCLUSIVE';
      case 'not_measurable':
        return 'NOT MEASURABLE';
      default:
        return status.toUpperCase();
    }
  }

  private titleFromKey(key: string): string {
    return key.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase());
  }
}
