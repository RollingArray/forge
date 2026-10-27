import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ContentCardComponent } from '../../../../shared/components/content-card/content-card.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';

type EvidenceValue = string | number | boolean | null;

interface RelationshipMetric {
  label: string;
  value: string;
}

interface RelationshipRecord {
  key: string;
  title: string;
  source: string;
  target: string;
  relationshipType: string;
  status: string;
  statusLabel: string;
  note: string;
  metrics: RelationshipMetric[];
}

@Component({
  selector: 'app-relationship-evidence',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    ContentCardComponent,
  ],
  templateUrl: './relationship-evidence.component.html',
  styleUrl: './relationship-evidence.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RelationshipEvidenceComponent {
  readonly evidence = input<Record<string, unknown> | null>(null);

  readonly records = () => {
    const root = this.asRecord(this.evidence());
    const groups = this.asRecord(root['relationships']);

    return Object.entries(groups).map(([key, raw]): RelationshipRecord => {
      const group = this.asRecord(raw);
      const status = this.statusOf(group);
      const sourceEntity = this.stringValue(
        group['source_entity'] ?? group['parent_entity'],
        'Unknown entity',
      );
      const targetEntity = this.stringValue(
        group['target_entity'] ?? group['child_entity'],
        'Unknown entity',
      );
      const sourceFields = this.stringList(
        group['source_fields'] ?? group['parent_fields'],
      );
      const targetFields = this.stringList(
        group['target_fields'] ?? group['child_fields'],
      );

      const metricKeys = [
        'parent_rows_checked',
        'parent_rows_with_null_key',
        'parent_keys',
        'duplicate_parent_key_rows',
        'child_rows_checked',
        'matched_child_rows',
        'orphan_child_rows',
        'null_reference_rows',
        'partial_null_reference_rows',
        'mandatory_child_reference_violations',
        'participating_parent_keys',
        'parents_without_children',
        'parent_participation_rate',
        'mandatory_parent_participation_violations',
        'minimum_children_per_parent',
        'maximum_children_per_parent',
        'average_children_per_participating_parent',
        'one_to_one_cardinality_violations',
      ];

      const isLegacy = status === 'legacy';
      const directionSensitiveLegacyRelationship =
        isLegacy &&
        ['MANY_TO_ONE', 'MANY_TO_MANY'].includes(
          this.stringValue(group['relationship_type'], '').toUpperCase(),
        );

      const metrics = directionSensitiveLegacyRelationship
        ? []
        : metricKeys
            .filter((name) => Object.prototype.hasOwnProperty.call(group, name))
            .filter((name) => group[name] !== null && group[name] !== undefined)
            .map((name) => ({
              label: this.labelFor(name),
              value: this.formatValue(name, group[name] as EvidenceValue),
            }));

      const legacyNote = directionSensitiveLegacyRelationship
        ? 'This saved measurement predates relationship-direction handling. '
          + 'Orphan counts and parent-child cardinality metrics are suppressed '
          + 'because their direction cannot be trusted. The saved job has not '
          + 'been remeasured.'
        : '';

      return {
        key,
        title: this.titleFor(key),
        source: this.formatEntityFields(sourceEntity, sourceFields),
        target: this.formatEntityFields(targetEntity, targetFields),
        relationshipType: this.stringValue(group['relationship_type'], 'Unspecified'),
        status,
        statusLabel: this.statusLabel(status),
        note: legacyNote || this.stringValue(group['measurement_note'], ''),
        metrics,
      };
    });
  };

  private asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, unknown>)
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

  private statusOf(group: Record<string, unknown>): string {
    const raw = group['measurement_status'];
    if (raw === 'measured' || raw === 'inconclusive' || raw === 'not_measurable') {
      return raw;
    }

    return 'legacy';
  }

  private statusLabel(status: string): string {
    switch (status) {
      case 'measured':
        return 'Measured';
      case 'inconclusive':
        return 'Inconclusive';
      case 'not_measurable':
        return 'Not measurable';
      default:
        return 'Saved legacy evidence';
    }
  }

  private formatEntityFields(entity: string, fields: string[]): string {
    return fields.length ? entity + ' · ' + fields.join(', ') : entity;
  }

  private titleFor(key: string): string {
    return key.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase());
  }

  private labelFor(key: string): string {
    const labels: Record<string, string> = {
      parent_rows_checked: 'Parent rows checked',
      parent_rows_with_null_key: 'Parent rows with missing keys',
      parent_keys: 'Distinct usable parent keys',
      duplicate_parent_key_rows: 'Duplicate parent-key rows',
      child_rows_checked: 'Child rows checked',
      matched_child_rows: 'Matched child references',
      orphan_child_rows: 'Orphan child references',
      null_reference_rows: 'Fully missing references',
      partial_null_reference_rows: 'Partially missing composite references',
      mandatory_child_reference_violations: 'Missing mandatory child references',
      participating_parent_keys: 'Parents with children',
      parents_without_children: 'Parents without children',
      parent_participation_rate: 'Parent participation rate',
      mandatory_parent_participation_violations: 'Mandatory parents without children',
      minimum_children_per_parent: 'Minimum children per parent',
      maximum_children_per_parent: 'Maximum children per parent',
      average_children_per_participating_parent: 'Average children per participating parent',
      one_to_one_cardinality_violations: 'One-to-one cardinality violations',
    };

    return labels[key] ?? key.replaceAll('_', ' ');
  }

  private formatValue(key: string, value: EvidenceValue): string {
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }

    if (typeof value === 'number' && key === 'parent_participation_rate') {
      return new Intl.NumberFormat('en', {
        style: 'percent',
        maximumFractionDigits: 2,
      }).format(value);
    }

    if (typeof value === 'number') {
      return Number.isInteger(value) ? String(value) : value.toFixed(3);
    }

    return value === null ? 'Not available' : String(value);
  }
}
