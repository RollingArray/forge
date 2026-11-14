import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { ValidationRuleResult } from '../../../../core/interfaces/validation-rule-result.interface';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { ContentGridComponent } from '../../../../shared/components/content-grid/content-grid.component';
import { ContentCardComponent } from '../../../../shared/components/content-card/content-card.component';
import { WorkspaceSimpleTableComponent } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkspaceSimpleTableColumn } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.models';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';

interface PopulationValidationRow {
  entity: string;
  requestedRows: string | number;
  generatedRows: string | number;
  difference: string | number;
  complete: string;
}

interface EvidenceTableRow {
  key: string;
  entity: string;
  identityFields: string;
  constraint: string;
  field: string;
  rule: string;
  expectedFields: string;
  actualFields: string;
  missingFields: string;
  unexpectedFields: string;
  source: string;
  target: string;
  sourceRows: string;
  targetRows: string;
  targetKeys: string;
  invalidReferences: string;
  missingCount: string;
  evaluationErrors: string;
  cardinality: string;
  participation: string;
  rowsChecked: string;
  parentRowsChecked: string;
  danglingReferences: string;
  duplicateReferences: string;
  permittedDomain: string;
  invalidValues: string;
  missingValues: string;
  conversionErrors: string;
  status: string;
}

interface DetailTableRow {
  key: string;
  property: string;
  value: string;
}

interface RuleCategoryGroup {
  category: string;
  label: string;
  rules: ValidationRuleResult[];
  passed: number;
  failed: number;
  notEvaluated: number;
  populationRows: PopulationValidationRow[];
  evidenceRows: EvidenceTableRow[];
}

@Component({
  selector: 'app-validation-rule-results',
  standalone: true,
  imports: [
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    MetricGridComponent,
    ContentGridComponent,
    ContentCardComponent,
    WorkspaceSimpleTableComponent,
  ],
  templateUrl: './validation-rule-results.component.html',
  styleUrl: './validation-rule-results.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ValidationRuleResultsComponent {
  readonly populationColumns: readonly WorkspaceSimpleTableColumn<PopulationValidationRow>[] = [
    {
      key: 'entity',
      label: 'Entity',
      width: 'minmax(180px, 1.5fr)',
    },
    {
      key: 'requestedRows',
      label: 'Requested Rows',
      width: 'minmax(130px, 1fr)',
      align: 'right',
    },
    {
      key: 'generatedRows',
      label: 'Generated Rows',
      width: 'minmax(140px, 1fr)',
      align: 'right',
    },
    {
      key: 'difference',
      label: 'Difference',
      width: 'minmax(110px, 0.8fr)',
      align: 'right',
    },
    {
      key: 'complete',
      label: 'Complete',
      width: '110px',
      align: 'center',
    },
  ];

  readonly identityColumns: readonly WorkspaceSimpleTableColumn<EvidenceTableRow>[] = [
    { key: 'entity', label: 'Entity', width: 'minmax(150px, 1.2fr)' },
    { key: 'identityFields', label: 'Identity Fields', width: 'minmax(180px, 1.5fr)' },
    { key: 'rowsChecked', label: 'Rows Checked', align: 'right' },
    { key: 'targetRows', label: 'Unique Identities', align: 'right' },
    { key: 'invalidReferences', label: 'Duplicates', type: 'error-count', align: 'right' },
    { key: 'missingCount', label: 'Missing Fields', type: 'error-count', align: 'right' },
    { key: 'status', label: 'Status', type: 'status', width: '110px', align: 'center' },
  ];

  readonly schemaColumns: readonly WorkspaceSimpleTableColumn<EvidenceTableRow>[] = [
    { key: 'entity', label: 'Entity', width: 'minmax(140px, 1fr)' },
    { key: 'expectedFields', label: 'Expected Fields', align: 'right' },
    { key: 'actualFields', label: 'Actual Fields', align: 'right' },
    { key: 'missingFields', label: 'Missing Fields', width: 'minmax(150px, 1.2fr)' },
    { key: 'unexpectedFields', label: 'Unexpected Fields', width: 'minmax(150px, 1.2fr)' },
    { key: 'rowsChecked', label: 'Rows Checked', align: 'right' },
    { key: 'status', label: 'Status', type: 'status', width: '110px', align: 'center' },
  ];

  readonly foreignKeyColumns: readonly WorkspaceSimpleTableColumn<EvidenceTableRow>[] = [
    { key: 'constraint', label: 'Foreign Key', width: 'minmax(140px, 1fr)' },
    { key: 'source', label: 'Source', width: 'minmax(160px, 1.2fr)' },
    { key: 'target', label: 'Target', width: 'minmax(160px, 1.2fr)' },
    { key: 'sourceRows', label: 'Source Rows', align: 'right' },
    { key: 'targetKeys', label: 'Target Keys', align: 'right' },
    { key: 'invalidReferences', label: 'Invalid References', type: 'error-count', align: 'right' },
    { key: 'missingCount', label: 'Missing Fields', type: 'error-count', align: 'right' },
    { key: 'status', label: 'Status', type: 'status', width: '110px', align: 'center' },
  ];

  readonly relationshipColumns: readonly WorkspaceSimpleTableColumn<EvidenceTableRow>[] = [
    { key: 'source', label: 'Source', width: 'minmax(150px, 1.2fr)' },
    { key: 'target', label: 'Target', width: 'minmax(150px, 1.2fr)' },
    { key: 'cardinality', label: 'Cardinality' },
    { key: 'participation', label: 'Participation', width: 'minmax(130px, 1fr)' },
    { key: 'rowsChecked', label: 'Child Rows', align: 'right' },
    { key: 'parentRowsChecked', label: 'Parent Rows', align: 'right' },
    { key: 'danglingReferences', label: 'Dangling References', type: 'error-count', align: 'right' },
    { key: 'duplicateReferences', label: 'Duplicate References', type: 'error-count', align: 'right' },
    { key: 'status', label: 'Status', type: 'status', width: '110px', align: 'center' },
  ];

  readonly constraintColumns: readonly WorkspaceSimpleTableColumn<EvidenceTableRow>[] = [
    { key: 'constraint', label: 'Constraint', width: 'minmax(150px, 1.2fr)' },
    { key: 'entity', label: 'Entity' },
    { key: 'field', label: 'Field' },
    { key: 'rule', label: 'Rule', width: 'minmax(150px, 1.2fr)' },
    { key: 'rowsChecked', label: 'Rows Checked', align: 'right' },
    { key: 'invalidValues', label: 'Violations', type: 'error-count', align: 'right' },
    { key: 'missingCount', label: 'Missing Fields', type: 'error-count', align: 'right' },
    { key: 'evaluationErrors', label: 'Evaluation Errors', type: 'error-count', align: 'right' },
    { key: 'status', label: 'Status', type: 'status', width: '110px', align: 'center' },
  ];

  readonly domainColumns: readonly WorkspaceSimpleTableColumn<EvidenceTableRow>[] = [
    { key: 'entity', label: 'Entity' },
    { key: 'field', label: 'Field' },
    { key: 'permittedDomain', label: 'Permitted Domain', width: 'minmax(180px, 1.5fr)' },
    { key: 'rowsChecked', label: 'Rows Checked', align: 'right' },
    { key: 'invalidValues', label: 'Invalid Values', type: 'error-count', align: 'right' },
    { key: 'missingValues', label: 'Missing Values', type: 'error-count', align: 'right' },
    { key: 'conversionErrors', label: 'Conversion Errors', type: 'error-count', align: 'right' },
    { key: 'status', label: 'Status', type: 'status', width: '110px', align: 'center' },
  ];

  readonly detailColumns: readonly WorkspaceSimpleTableColumn<DetailTableRow>[] = [
    { key: 'property', label: 'Property', width: 'minmax(220px, 1fr)' },
    { key: 'value', label: 'Value', width: 'minmax(0, 2fr)' },
  ];

  readonly rules = input.required<readonly ValidationRuleResult[]>();

  private readonly normalizedRules = computed(() =>
    this.rules().map((rule) => ({
      ...rule,
      normalizedStatus: rule.status.trim().toUpperCase(),
    })),
  );

  readonly summary = computed(() => {
    const rules = this.normalizedRules();

    return {
      total: rules.length,
      passed: rules.filter(
        (rule) => rule.normalizedStatus === 'PASSED',
      ).length,
      failed: rules.filter(
        (rule) => rule.normalizedStatus === 'FAILED',
      ).length,
      notEvaluated: rules.filter(
        (rule) =>
          rule.evaluated === false ||
          ['NOT_EVALUATED', 'NOT EVALUATED'].includes(rule.normalizedStatus),
      ).length,
    };
  });

  readonly metrics = computed<MetricCardData[]>(() => {
    const summary = this.summary();

    return [
      {
        label: 'Total rules',
        value: summary.total,
        description: 'All validation rules',
        icon: 'rule',
      },
      {
        label: 'Passed',
        value: summary.passed,
        description: 'Rules successfully evaluated',
        icon: 'check_circle',
      },
      {
        label: 'Failed',
        value: summary.failed,
        description: 'Rules with failed outcomes',
        icon: 'cancel',
      },
      {
        label: 'Not evaluated',
        value: summary.notEvaluated,
        description: 'Rules not evaluated',
        icon: 'pending_actions',
      },
    ];
  });

  readonly groups = computed<RuleCategoryGroup[]>(() => {
    const grouped = new Map<string, ValidationRuleResult[]>();

    for (const rule of this.rules()) {
      const category = rule.category || 'OTHER';
      const existing = grouped.get(category) ?? [];
      existing.push(rule);
      grouped.set(category, existing);
    }

    return Array.from(grouped, ([category, rules]) => ({
      category,
      label: this.categoryLabel(category),
      rules,
      passed: rules.filter(
        (rule) => rule.status.trim().toUpperCase() === 'PASSED',
      ).length,
      failed: rules.filter(
        (rule) => rule.status.trim().toUpperCase() === 'FAILED',
      ).length,
      notEvaluated: rules.filter(
        (rule) =>
          rule.evaluated === false ||
          ['NOT_EVALUATED', 'NOT EVALUATED'].includes(
            rule.status.trim().toUpperCase(),
          ),
      ).length,
      populationRows: category === 'POPULATION'
        ? rules.map((rule) => this.toPopulationRow(rule))
        : [],
      evidenceRows: category === 'POPULATION'
        ? []
        : rules.map((rule) => this.toEvidenceRow(rule)),
    }));
  });

  private toPopulationRow(rule: ValidationRuleResult): PopulationValidationRow {
    const details = rule.details ?? {};

    const normalizedDetails = new Map(
      Object.entries(details).map(([key, value]) => [
        key.toLowerCase().replace(/[^a-z0-9]/g, ''),
        value,
      ]),
    );

    const readValue = (keys: string[]): unknown => {
      for (const key of keys) {
        const value = normalizedDetails.get(key);
        if (value !== undefined && value !== null) {
          return value;
        }
      }
      return '—';
    };

    const numberFormatter = new Intl.NumberFormat('en-IN', {
      maximumFractionDigits: 20,
    });

    const displayValue = (value: unknown): string | number => {
      if (typeof value === 'number') {
        return Number.isFinite(value) ? numberFormatter.format(value) : String(value);
      }
      if (typeof value === 'string' && value.trim() !== '') {
        const numeric = Number(value);
        return Number.isFinite(numeric) ? numberFormatter.format(numeric) : value;
      }
      if (typeof value === 'boolean') {
        return value ? 'Yes' : 'No';
      }
      return value === null || value === undefined ? '—' : String(value);
    };

    const entity = rule.rule_id.includes(':')
      ? rule.rule_id.substring(rule.rule_id.indexOf(':') + 1)
      : rule.rule_id;

    const completeValue = readValue(['complete', 'iscomplete']);

    return {
      entity,
      requestedRows: displayValue(
        readValue(['requestedrows', 'requestedrowcount']),
      ),
      generatedRows: displayValue(
        readValue(['generatedrows', 'generatedrowcount']),
      ),
      difference: displayValue(
        readValue(['difference', 'rowdifference', 'differenceinrows']),
      ),
      complete:
        completeValue === true || String(completeValue).toLowerCase() === 'true'
          ? 'Yes'
          : completeValue === false || String(completeValue).toLowerCase() === 'false'
            ? 'No'
            : String(completeValue),
    };
  }

  private toEvidenceRow(rule: ValidationRuleResult): EvidenceTableRow {
    const details = rule.details ?? {};
    const read = (...keys: string[]): unknown => {
      for (const key of keys) {
        if (details[key] !== undefined && details[key] !== null) {
          return details[key];
        }
      }
      return null;
    };

    const display = (value: unknown): string => {
      if (value === null || value === undefined || value === '') return '—';
      if (Array.isArray(value)) {
        return value.map((item) => this.formatValue(item)).join(', ') || '—';
      }
      if (typeof value === 'number') {
        return Number.isFinite(value)
          ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: 20 }).format(value)
          : String(value);
      }
      if (typeof value === 'string' && value.trim() !== '') {
        const numeric = Number(value);
        return Number.isFinite(numeric)
          ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: 20 }).format(numeric)
          : value;
      }
      return this.formatValue(value);
    };

    const entityFromRule = rule.rule_id.includes(':')
      ? rule.rule_id.substring(rule.rule_id.indexOf(':') + 1)
      : rule.rule_id;

    const entity = display(read('entity') ?? entityFromRule);
    const sourceEntity = display(read('source_entity') ?? read('source'));
    const targetEntity = display(read('target_entity') ?? read('target'));
    const sourceFields = display(read('source_fields') ?? read('source_field'));
    const targetFields = display(read('target_fields') ?? read('target_field'));
    const source = sourceEntity === '—'
      ? sourceEntity
      : `${sourceEntity}${sourceFields !== '—' ? `.${sourceFields}` : ''}`;
    const target = targetEntity === '—'
      ? targetEntity
      : `${targetEntity}${targetFields !== '—' ? `.${targetFields}` : ''}`;

    const allowedValues = read('allowed_values');
    const min = read('min');
    const max = read('max');
    const domainParts: string[] = [];
    if (allowedValues !== null) domainParts.push(`Allowed: ${display(allowedValues)}`);
    if (min !== null || max !== null) {
      domainParts.push(`Range: ${min === null ? '—' : display(min)} to ${max === null ? '—' : display(max)}`);
    }

    const operator = display(read('operator'));
    const expected = display(read('expected'));
    const ruleDescription = operator === '—'
      ? expected
      : `${operator}${expected !== '—' ? ` ${expected}` : ''}`;

    const participation = [
      read('source_participation'),
      read('target_participation'),
    ].filter((value) => value !== null).map((value) => display(value)).join(' / ');

    return {
      key: rule.rule_id,
      entity,
      identityFields: display(read('identity_fields')),
      constraint: display(read('name') ?? read('foreign_key_name') ?? rule.rule_id.split(':').slice(1).join(':')),
      field: display(read('field')),
      rule: ruleDescription,
      expectedFields: display(read('expected_field_count')),
      actualFields: display(read('actual_field_count')),
      missingFields: display(read('missing_fields')),
      unexpectedFields: display(read('unexpected_fields')),
      source,
      target,
      sourceRows: display(read('source_rows_checked')),
      targetRows: display(read('unique_identities') ?? read('target_keys_available')),
      targetKeys: display(read('target_keys_available')),
      invalidReferences: display(read('invalid_reference_count') ?? read('duplicate_count')),
      missingCount: display(read('missing_field_count')),
      evaluationErrors: display(read('evaluation_error_count')),
      cardinality: display(read('type')),
      participation: participation || '—',
      rowsChecked: display(read('rows_checked') ?? read('child_rows_checked')),
      parentRowsChecked: display(read('parent_rows_checked')),
      danglingReferences: display(read('dangling_reference_count')),
      duplicateReferences: display(read('duplicate_child_reference_rows')),
      permittedDomain: domainParts.join(' | ') || '—',
      invalidValues: display(read('violation_count') ?? read('invalid_count')),
      missingValues: display(read('missing_count')),
      conversionErrors: display(read('conversion_error_count')),
      status: this.statusLabel(rule),
    };
  }

  ruleTitle(rule: ValidationRuleResult): string {
    const [ruleType, target = ''] = rule.rule_id.split(':', 2);
    const targetParts = target.split('.');
    const field = targetParts.slice(1).join('.');

    if (ruleType.toLowerCase() === 'semantic_unique') {
      return `${this.humanizeIdentifier(field || target || 'Field')} must be unique`;
    }

    const readableType = this.humanizeIdentifier(ruleType);
    const readableTarget = target
      ? this.humanizeIdentifier(target.replaceAll('.', ' '))
      : '';

    return readableTarget
      ? `${readableType}: ${readableTarget}`
      : readableType;
  }

  ruleEntity(rule: ValidationRuleResult): string {
    const target = rule.rule_id.split(':', 2)[1] ?? '';
    const entity = target.split('.')[0];

    return entity ? this.humanizeIdentifier(entity) : 'General';
  }

  private humanizeIdentifier(value: string): string {
    return value
      .replaceAll('_', ' ')
      .replaceAll('.', ' ')
      .toLowerCase()
      .replace(/\\b\\w/g, (character) => character.toUpperCase());
  }

  hasDiagnostic(rule: ValidationRuleResult): boolean {
    return this.statusLabel(rule) !== 'Passed';
  }

  categoryLabel(category: string): string {
    const labels: Record<string, string> = {
      POPULATION: 'Population',
      IDENTITY: 'Identity',
      SCHEMA: 'Schema',
      FOREIGN_KEY: 'Foreign key',
      RELATIONSHIP_CARDINALITY: 'Relationship cardinality',
      CONSTRAINT: 'Business constraints',
      DOMAIN: 'Domain validity',
    };

    return labels[category] ??
      category.replaceAll('_', ' ').toLowerCase()
        .replace(/\b\w/g, (character) => character.toUpperCase());
  }

  categoryDescription(category: string): string {
    const descriptions: Record<string, string> = {
      POPULATION: 'Verify requested and generated row counts for each entity.',
      IDENTITY: 'Verify that generated records satisfy their identity requirements.',
      SCHEMA: 'Verify field structure, data types, and schema requirements.',
      FOREIGN_KEY: 'Verify foreign-key values and referential integrity.',
      RELATIONSHIP_CARDINALITY: 'Verify relationship counts and cardinality requirements.',
      CONSTRAINT: 'Verify business constraints against generated data.',
      DOMAIN: 'Verify generated values against their permitted domains.',
    };

    return descriptions[category] ?? 'Inspect the deterministic validation rules for this dimension.';
  }

  iconFor(category: string): string {
    const icons: Record<string, string> = {
      POPULATION: 'database',
      IDENTITY: 'fingerprint',
      SCHEMA: 'schema',
      FOREIGN_KEY: 'link',
      RELATIONSHIP_CARDINALITY: 'account_tree',
      CONSTRAINT: 'rule',
      DOMAIN: 'verified_user',
    };

    return icons[category] ?? 'analytics';
  }

  statusLabel(rule: ValidationRuleResult): string {
    const status = rule.status.trim().toUpperCase();

    if (
      rule.evaluated === false ||
      status === 'NOT_EVALUATED' ||
      status === 'NOT EVALUATED'
    ) {
      return 'Not evaluated';
    }

    if (status === 'PASSED') {
      return 'Passed';
    }

    if (status === 'FAILED') {
      return 'Failed';
    }

    return rule.status;
  }

  statusClass(rule: ValidationRuleResult): string {
    const status = rule.status.trim().toUpperCase();

    if (status === 'PASSED') {
      return 'passed';
    }

    if (status === 'FAILED') {
      return 'failed';
    }

    return 'pending';
  }

  detailRows(rule: ValidationRuleResult): DetailTableRow[] {
    return Object.entries(rule.details ?? {}).map(([key, value]) => ({
      key,
      property: key.replaceAll('_', ' ').replace(/\b\w/g, (character) =>
        character.toUpperCase(),
      ),
      value: this.formatValue(value),
    }));
  }

  private formatValue(value: unknown): string {
    if (value === null || value === undefined) {
      return 'Not available';
    }

    if (Array.isArray(value)) {
      return value.map((item) => this.formatValue(item)).join(', ') || 'None';
    }

    if (typeof value === 'object') {
      return JSON.stringify(value);
    }

    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }

    return String(value);
  }
}
