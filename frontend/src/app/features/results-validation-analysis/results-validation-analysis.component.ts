import { CommonModule } from '@angular/common';
import {
  Component,
  ChangeDetectionStrategy,
  inject,
  DestroyRef,
  signal,
  computed,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { ForgeSpecification } from '../../core/interfaces/forge-specification.interface';
import { ValidationCheck } from '../../core/interfaces/validation-check.interface';
import { SpecificationService } from '../../core/services/specification.service';
import { CheckStatus } from '../../core/types/check-status.type';
import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import { WorkflowRowComponent } from '../../shared/components/workflow-row/workflow-row.component';
import {
  WorkflowStepItem,
  WorkflowStep,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';
import type { WorkspaceToolbarFilter } from '../../shared/components/workspace-table-toolbar/workspace-table-toolbar.component';
import { GenerationJobResponse } from '../generate/models/generation.models';
import { GenerationService } from '../generate/services/generation.service';
import { GenerationValidationSummary } from '../results/results.models';
import { ResultsValidationSummaryComponent } from './components/results-validation-summary/results-validation-summary.component';
import { ValidationEvidenceComponent } from './components/validation-evidence/validation-evidence.component';
import { ValidationFindingsComponent } from './components/validation-findings/validation-findings.component';

import type { ValidationFinding } from '../../core/interfaces/validation-finding.interface';
@Component({
  selector: 'app-results-validation-analysis',
  standalone: true,
  imports: [
    CommonModule,
    WorkflowPageComponent,
    WorkflowRowComponent,
    ResultsValidationSummaryComponent,
    ValidationEvidenceComponent,
    ValidationFindingsComponent,
  ],
  templateUrl: './results-validation-analysis.component.html',
  styleUrl: './results-validation-analysis.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsValidationAnalysisComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly generationService = inject(GenerationService);
  private readonly specificationService = inject(SpecificationService);
  private readonly destroyRef = inject(DestroyRef);

  readonly steps: readonly WorkflowStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];

  readonly activeStep: WorkflowStep = 'results';

  readonly dataModelId = this.route.snapshot.paramMap.get('dataModelId') ?? '';
  readonly jobId = this.route.snapshot.paramMap.get('jobId') ?? '';

  readonly job = signal<GenerationJobResponse | null>(null);
  readonly specification = signal<ForgeSpecification | null>(null);
  readonly modelName = computed(() => this.specification()?.model.name ?? 'Data Model');
  readonly modelDescription = computed(() => this.specification()?.model.description ?? '');
  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);
  readonly searchTerm = signal('');
  readonly activeFindingFilter = signal<'all' | 'error' | 'warning'>('all');

  readonly validation = computed<GenerationValidationSummary | null>(
    () => this.job()?.validation ?? null,
  );

  readonly evidenceSections = computed<ValidationCheck[]>(() => {
    const evidence = this.validation()?.evidence;
    if (!evidence) {
      return [];
    }

    const definitions: Record<string, { title: string; description: string; issueKey: string }> = {
      completeness: {
        title: 'Row completeness',
        description: 'Checks whether each entity contains the number of records requested.',
        issueKey: 'difference',
      },
      schema: {
        title: 'Schema conformance',
        description: 'Compares generated fields with the expected entity structure.',
        issueKey: 'entities_with_missing_fields',
      },
      primary_keys: {
        title: 'Primary key integrity',
        description: 'Checks for missing identity values and duplicate records.',
        issueKey: 'duplicate_count',
      },
      foreign_keys: {
        title: 'Foreign key integrity',
        description: 'Checks references between related entities.',
        issueKey: 'invalid_reference_count',
      },
      constraints: {
        title: 'Business constraints',
        description: 'Checks generated values against configured business rules.',
        issueKey: 'violation_count',
      },
      domain_validity: {
        title: 'Value validity',
        description: 'Checks values against configured allowed values and ranges.',
        issueKey: 'invalid_count',
      },
      null_completeness: {
        title: 'Missing values',
        description: 'Measures missing values across checked fields.',
        issueKey: 'missing_count',
      },
      coverage: {
        title: 'Validation coverage',
        description: 'Shows how many declared checks were actually evaluated.',
        issueKey: '',
      },
    };

    return Object.entries(evidence).map(([key, raw]) => {
      const definition = definitions[key] ?? {
        title: this.titleFromKey(key),
        description: 'Summary of the checks performed.',
        issueKey: '',
      };
      const data = this.asRecord(raw);

      const metrics = Object.entries(data)
        .filter(
          ([name, value]) =>
            name !== 'entities' &&
            name !== 'relationships' &&
            name !== 'constraints' &&
            name !== 'fields' &&
            name !== 'difference' &&
            (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'string'),
        )
        .map(([name, value]) => ({
          label: this.friendlyLabel(name),
          value: typeof value === 'boolean' ? (value ? 'Yes' : 'No') : (value as string | number),
        }));

      const recordKey = ['entities', 'relationships', 'constraints', 'fields'].find(
        (name) => data[name] && typeof data[name] === 'object',
      );

      const nested = recordKey ? this.asRecord(data[recordKey]) : {};
      const records = Object.entries(nested).map(([name, value]) => {
        const fields = this.asRecord(value);
        return {
          label: name,
          details: Object.entries(fields)
            .filter(
              ([, fieldValue]) =>
                fieldValue === null ||
                ['string', 'number', 'boolean'].includes(typeof fieldValue) ||
                Array.isArray(fieldValue),
            )
            .map(([fieldName, fieldValue]) => ({
              label: this.friendlyLabel(fieldName),
              value: Array.isArray(fieldValue)
                ? fieldValue.map((item) => String(item)).join(', ') || 'None'
                : fieldValue === null
                  ? 'Not available'
                  : typeof fieldValue === 'boolean'
                    ? fieldValue
                      ? 'Yes'
                      : 'No'
                    : (fieldValue as string | number),
            })),
        };
      });

      const issueValue = definition.issueKey ? data[definition.issueKey] : undefined;
      const issueCount = typeof issueValue === 'number' ? issueValue : null;
      const explicitlyPassed = key === 'completeness' && data['complete'] === true;
      const hasIssues = issueCount !== null && issueCount > 0;
      const notChecked = records.length === 0 && metrics.length === 0;

      const isCoverage = key === 'coverage';
      const status: CheckStatus = isCoverage
        ? notChecked
          ? 'not-checked'
          : 'passed'
        : notChecked
          ? 'not-checked'
          : hasIssues
            ? 'review'
            : explicitlyPassed || issueCount === 0 || issueCount !== null
              ? 'passed'
              : 'not-checked';

      return {
        key,
        title: definition.title,
        description: definition.description,
        status,
        statusLabel: isCoverage && !notChecked
          ? 'Coverage available'
          : status === 'passed'
            ? 'No issues reported'
            : status === 'review'
              ? 'Review required'
              : 'Evidence unavailable',
        issueCount,
        metrics,
        records,
      };
    });
  });


  readonly relationshipEvidenceCheck = computed<ValidationCheck | null>(() => {
    const quality = this.asRecord(this.job()?.quality);
    const evidence = this.asRecord(quality['relationship_fidelity']);
    const groups = this.asRecord(evidence['relationships']);
    const entries = Object.entries(groups);

    if (entries.length === 0) {
      return null;
    }

    const counts = {
      measured: 0,
      inconclusive: 0,
      not_measurable: 0,
      legacy: 0,
    };

    const readString = (value: unknown, fallback: string): string =>
      typeof value === 'string' && value.trim() ? value : fallback;

    const readFields = (value: unknown): string[] =>
      Array.isArray(value)
        ? value.filter((item): item is string => typeof item === 'string')
        : [];

    const records: ValidationCheck['records'] = entries.map(([key, raw]) => {
      const group = this.asRecord(raw);
      const relationshipType = readString(
        group['relationship_type'],
        'Unspecified',
      );
      const rawStatus = readString(group['measurement_status'], 'legacy');
      const status = rawStatus in counts
        ? rawStatus as keyof typeof counts
        : 'legacy';

      counts[status] += 1;

      const source = readString(
        group['source_entity'] ?? group['parent_entity'],
        'Unknown entity',
      );
      const target = readString(
        group['target_entity'] ?? group['child_entity'],
        'Unknown entity',
      );
      const sourceFields = readFields(
        group['source_fields'] ?? group['parent_fields'],
      );
      const targetFields = readFields(
        group['target_fields'] ?? group['child_fields'],
      );

      const details: ValidationCheck['records'][number]['details'] = [
        { label: 'Relationship type', value: relationshipType },
        {
          label: 'Source',
          value: sourceFields.length
            ? `${source} · ${sourceFields.join(', ')}`
            : source,
        },
        {
          label: 'Target',
          value: targetFields.length
            ? `${target} · ${targetFields.join(', ')}`
            : target,
        },
        {
          label: 'Evidence status',
          value: status === 'measured'
            ? 'Measured'
            : status === 'inconclusive'
              ? 'Inconclusive'
              : status === 'not_measurable'
                ? 'Not measurable'
                : 'Saved legacy evidence',
        },
      ];

      const suppressLegacyMetrics =
        status === 'legacy' &&
        ['MANY_TO_ONE', 'MANY_TO_MANY'].includes(
          relationshipType.toUpperCase(),
        );

      if (suppressLegacyMetrics) {
        details.push({
          label: 'Measurement note',
          value:
            'Saved legacy evidence. Direction-sensitive orphan and cardinality metrics are suppressed; this job has not been remeasured.',
        });
      } else {
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

        for (const key of metricKeys) {
          const value = group[key];

          if (
            value === null ||
            value === undefined ||
            !['string', 'number', 'boolean'].includes(typeof value)
          ) {
            continue;
          }

          const formattedValue =
            key === 'parent_participation_rate' && typeof value === 'number'
              ? new Intl.NumberFormat('en', {
                  style: 'percent',
                  maximumFractionDigits: 2,
                }).format(value)
              : typeof value === 'boolean'
                ? value ? 'Yes' : 'No'
                : typeof value === 'number' && !Number.isInteger(value)
                  ? value.toFixed(3)
                  : String(value);

          details.push({
            label: this.friendlyLabel(key),
            value: formattedValue,
          });
        }

        const note = group['measurement_note'];
        if (typeof note === 'string' && note.trim()) {
          details.push({ label: 'Measurement note', value: note });
        }
      }

      return {
        label: key.replaceAll('_', ' ').replace(/\b\w/g, (character) =>
          character.toUpperCase(),
        ),
        details,
      };
    });

    const metrics: ValidationCheck['metrics'] = [
      { label: 'Relationships analyzed', value: entries.length },
      { label: 'Measured', value: counts.measured },
      { label: 'Inconclusive', value: counts.inconclusive },
      { label: 'Not measurable', value: counts.not_measurable },
      { label: 'Saved legacy evidence', value: counts.legacy },
    ];

    const allMeasured = counts.measured === entries.length;

    return {
      key: 'relationship_fidelity',
      title: 'Relationship Fidelity',
      description:
        'Reviews relationship measurements and per-relationship evidence saved with this generation job.',
      status: allMeasured ? 'passed' : 'not-checked',
      statusLabel: allMeasured
        ? 'Measurements available'
        : 'Evidence requires review',
      issueCount: null,
      metrics,
      records,
    };
  });

  readonly allEvidenceSections = computed<ValidationCheck[]>(() => {
    const checks = this.evidenceSections();
    const relationshipCheck = this.relationshipEvidenceCheck();
    return relationshipCheck ? [...checks, relationshipCheck] : checks;
  });

  readonly toolbarFilters = computed<WorkspaceToolbarFilter[]>(() => [
    {
      id: 'all',
      label: 'All',
      icon: 'fact_check',
      count: this.findings().length,
      active: this.activeFindingFilter() === 'all',
    },
    {
      id: 'error',
      label: 'Errors',
      icon: 'error',
      count: this.errorCount(),
      active: this.activeFindingFilter() === 'error',
      variant: 'danger',
    },
    {
      id: 'warning',
      label: 'Warnings',
      icon: 'warning',
      count: this.warningCount(),
      active: this.activeFindingFilter() === 'warning',
      variant: 'warning',
    },
  ]);

  readonly findings = computed<ValidationFinding[]>(() => {
    const result = this.validation();
    if (!result) {
      return [];
    }

    return [
      ...result.errors.map((details, index) => ({
        id: index,
        severity: 'error' as const,
        title: this.findingTitle(details),
        details,
        category: this.findingCategory(details),
      })),
      ...result.warnings.map((details, index) => ({
        id: result.errors.length + index,
        severity: 'warning' as const,
        title: this.findingTitle(details),
        details,
        category: this.findingCategory(details),
      })),
    ];
  });

  readonly filteredFindings = computed(() => {
    const query = this.searchTerm().trim().toLowerCase();
    const filter = this.activeFindingFilter();

    return this.findings().filter((finding) => {
      if (filter !== 'all' && finding.severity !== filter) {
        return false;
      }

      return (
        !query ||
        [finding.title, finding.details, finding.category, finding.severity]
          .join(' ')
          .toLowerCase()
          .includes(query)
      );
    });
  });

  readonly errorCount = computed(() => this.validation()?.errors.length ?? 0);

  readonly warningCount = computed(() => this.validation()?.warnings.length ?? 0);

  readonly issueCount = computed(() => this.errorCount() + this.warningCount());

  constructor() {
    this.loadSpecification();
    this.loadGenerationJob();
  }

  updateSearch(value: string): void {
    this.searchTerm.set(value);
  }

  setFindingFilter(filter: string): void {
    if (filter === 'all' || filter === 'error' || filter === 'warning') {
      this.activeFindingFilter.set(filter);
    }
  }

  selectStep(step: WorkflowStep): void {
    if (!this.dataModelId) {
      return;
    }

    switch (step) {
      case 'model':
        this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'studio']);
        break;
      case 'validate':
        this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'validation']);
        break;
      case 'population':
        this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'population']);
        break;
      case 'generate':
        this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'generate']);
        break;
      case 'results':
        this.backToResults();
        break;
    }
  }

  backToResults(): void {
    if (!this.dataModelId || !this.jobId) {
      return;
    }

    this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'results', this.jobId]);
  }

  private loadSpecification(): void {
    if (!this.dataModelId) {
      return;
    }

    this.specificationService
      .getSpecification(this.dataModelId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (specification) => this.specification.set(specification),
        error: () => {
          // Keep the analysis available even if model metadata cannot load.
        },
      });
  }

  private loadGenerationJob(): void {
    if (!this.dataModelId || !this.jobId) {
      this.loadError.set('The data model ID or generation job ID is missing.');
      this.loading.set(false);
      return;
    }

    this.generationService
      .getGenerationJob(this.dataModelId, this.jobId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (job) => {
          this.job.set(job);
          this.loading.set(false);
        },
        error: () => {
          this.loadError.set('Validation analysis could not be loaded for this generation job.');
          this.loading.set(false);
        },
      });
  }

  private asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {};
  }

  private friendlyLabel(value: string): string {
    const labels: Record<string, string> = {
      entities_checked: 'Entities checked',
      entities_complete: 'Entities complete',
      total_requested_rows: 'Rows requested',
      total_generated_rows: 'Rows generated',
      complete: 'All requested rows generated',
      expected_field_count: 'Expected fields',
      actual_field_count: 'Generated fields',
      expected_fields: 'Expected fields',
      actual_fields: 'Generated fields',
      missing_fields: 'Missing fields',
      unexpected_fields: 'Unexpected fields',
      rows_checked: 'Rows checked',
      rows_with_missing_fields: 'Rows with missing fields',
      duplicate_count: 'Duplicate identities',
      missing_field_count: 'Missing identity values',
      unique_identities: 'Unique identities',
      identity_fields: 'Identity fields',
      constraints_checked: 'Constraints checked',
      violation_count: 'Violations',
      evaluation_error_count: 'Evaluation errors',
      invalid_reference_count: 'Invalid references',
      relationships_checked: 'Relationships checked',
      source_rows_checked: 'Source rows checked',
      target_keys_available: 'Target keys available',
      invalid_count: 'Invalid values',
      missing_count: 'Missing values',
      conversion_error_count: 'Conversion errors',
      missing_rate: 'Missing-value rate',
      fields_checked: 'Fields checked',
      null_fields_checked: 'Fields checked for missing values',
      domain_fields_checked: 'Fields checked for valid values',
      constraints_declared: 'Rules declared',
      relationships_declared: 'Relationships declared',
      entities_declared: 'Entities declared',
      entities_population_checked: 'Entities checked for row counts',
      entities_schema_checked: 'Entities checked for schema',
      entities_identity_checked: 'Entities checked for identity',
      min: 'Minimum allowed value',
      max: 'Maximum allowed value',
      allowed_values: 'Allowed values',
      requested_rows: 'Rows requested',
      generated_rows: 'Rows generated',
      difference: 'Row-count difference',
      source_entity: 'Source entity',
      target_entity: 'Referenced entity',
      source_fields: 'Source fields',
      target_fields: 'Referenced fields',
      entity: 'Entity',
      field: 'Field',
      operator: 'Rule operator',
      expected: 'Expected value',
    };

    if (labels[value]) {
      return labels[value];
    }

    return this.titleFromKey(value);
  }

  private findingTitle(message: string): string {
    const firstLine = message.split(/\r?\n/, 1)[0].trim();
    if (!firstLine) {
      return 'Validation finding';
    }

    return firstLine.length > 100 ? `${firstLine.slice(0, 97)}…` : firstLine;
  }

  private findingCategory(message: string): string {
    const value = message.toLowerCase();

    if (value.includes('foreign key') || value.includes('reference')) {
      return 'Relationship';
    }
    if (
      value.includes('primary key') ||
      value.includes('identity') ||
      value.includes('duplicate')
    ) {
      return 'Identity';
    }
    if (value.includes('constraint')) {
      return 'Business rule';
    }
    if (value.includes('schema') || value.includes('field')) {
      return 'Schema';
    }
    if (value.includes('null') || value.includes('missing')) {
      return 'Completeness';
    }
    if (value.includes('domain') || value.includes('allowed value') || value.includes('range')) {
      return 'Value validity';
    }

    return 'Validation';
  }

  private titleFromKey(key: string): string {
    return key.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase());
  }
}
