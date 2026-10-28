import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import { WorkflowRowComponent } from '../../shared/components/workflow-row/workflow-row.component';
import {
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';
import { MetricCardData } from '../../shared/components/metric-grid/metric-card-data';

import { GenerationJobResponse } from '../generate/models/generation.models';
import { GenerationService } from '../generate/services/generation.service';
import { GenerationQualityProfile } from '../results/results.models';
import { ForgeSpecification } from '../../core/interfaces/forge-specification.interface';
import { SpecificationService } from '../../core/services/specification.service';
import { QualityEvidenceItem } from '../../core/interfaces/quality-evidence-item.interface';
import { QualityEvidenceSection } from '../../core/interfaces/quality-evidence-section.interface';
import { ResultsQualityAnalysisSummaryComponent } from './components/results-quality-analysis-summary/results-quality-analysis-summary.component';
import { QualityEvidenceComponent } from './components/quality-evidence/quality-evidence.component';


@Component({
  selector: 'app-results-quality-analysis',
  standalone: true,
  imports: [
    CommonModule,
    WorkflowPageComponent,
    WorkflowRowComponent,
    ResultsQualityAnalysisSummaryComponent,
    QualityEvidenceComponent,
  ],
  templateUrl: './results-quality-analysis.component.html',
  styleUrl: './results-quality-analysis.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsQualityAnalysisComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly generationService = inject(GenerationService);
  private readonly specificationService = inject(SpecificationService);
  private readonly destroyRef = inject(DestroyRef);

  readonly dataModelId = this.route.snapshot.paramMap.get('dataModelId') ?? '';
  readonly jobId = this.route.snapshot.paramMap.get('jobId') ?? '';

  readonly steps: readonly WorkflowStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];

  readonly activeStep: WorkflowStep = 'results';

  readonly job = signal<GenerationJobResponse | null>(null);
  readonly specification = signal<ForgeSpecification | null>(null);
  readonly modelName = computed(() => this.specification()?.model.name ?? 'Data Model');
  readonly modelDescription = computed(() => this.specification()?.model.description ?? '');
  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);

  readonly quality = computed<GenerationQualityProfile | null>(
    () => this.job()?.quality ?? null,
  );

  readonly populationFidelityProfile = computed<Record<string, unknown>>(
    () => this.asRecord(this.quality()?.population_fidelity),
  );

  readonly distributionFidelityProfile = computed<Record<string, unknown>>(
    () => this.asRecord(this.quality()?.distribution_fidelity),
  );

  readonly metrics = computed<MetricCardData[]>(() => {
    const quality = this.quality();
    if (!quality) {
      return [];
    }

    return [
      {
        label: 'Population fidelity',
        value: this.numberValue(quality.population_fidelity, 'fidelity_rate') === null
          ? 'Not available'
          : `${(this.numberValue(quality.population_fidelity, 'fidelity_rate')! * 100).toFixed(1)}%`,
        description: 'Requested population achieved',
        icon: 'verified',
      },
      {
        label: 'Relationships analyzed',
        value: this.numberValue(quality.relationship_fidelity, 'relationships_analyzed') ?? 'Not available',
        description: 'Relationships evaluated',
        icon: 'account_tree',
      },
      {
        label: 'Distributions analyzed',
        value: this.numberValue(quality.distribution_fidelity, 'fields_analyzed') ?? 'Not available',
        description: 'Fields analyzed for distributions',
        icon: 'pie_chart',
      },
      {
        label: 'Numeric fields analyzed',
        value: this.numberValue(quality.statistical_fidelity, 'numeric_fields_analyzed') ?? 'Not available',
        description: 'Numeric fields evaluated',
        icon: 'query_stats',
      },
      {
        label: 'Rows / second',
        value: this.numberValue(quality.performance, 'rows_per_second') === null
          ? 'Not available'
          : Math.round(this.numberValue(quality.performance, 'rows_per_second')!).toLocaleString('en-US'),
        description: 'Generation throughput',
        icon: 'speed',
      },
      {
        label: 'Identity spaces analyzed',
        value: this.numberValue(quality.identity_space_utilization, 'entities_analyzed') ?? 'Not available',
        description: 'Entity identity spaces evaluated',
        icon: 'key',
      },
    ];
  });

  readonly evidenceSections = computed<QualityEvidenceSection[]>(() => {
    const quality = this.quality();
    if (!quality) {
      return [];
    }

    const descriptions: Record<string, string> = {
      population_fidelity: 'How closely generated row counts match the requested population.',
      distribution_fidelity: 'Coverage of field-level distribution analysis.',
      relationship_fidelity: 'Evaluation of relationships between generated entities.',
      identity_space_utilization: 'Analysis of entity identity-space utilization.',
      statistical_fidelity: 'Statistical analysis of numeric fields.',
      performance: 'Observed generation performance measurements.',
      validation: 'Quality-related validation information recorded by the generation job.',
    };

    return Object.entries(quality).map(([key, raw]) => ({
      key,
      title: this.titleFromKey(key),
      description: descriptions[key] ?? 'Recorded quality evidence for this dimension.',
      items: this.flattenEvidence(this.asRecord(raw)),
    }));
  });

  constructor() {
    this.loadSpecification();
    this.loadGenerationJob();
  }

  private loadSpecification(): void {
    if (!this.dataModelId) return;
    this.specificationService.getSpecification(this.dataModelId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (specification) => this.specification.set(specification),
        error: () => {
          // Keep quality analysis available if model metadata cannot load.
        },
      });
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

    this.router.navigate([
      '/workspace',
      this.dataModelId,
      'data-model',
      'results',
      this.jobId,
    ]);
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
          this.loadError.set(
            'Quality analysis could not be loaded for this generation job.',
          );
          this.loading.set(false);
        },
      });
  }

  private numberValue(value: unknown, key: string): number | null {
    const raw = this.asRecord(value)[key];

    if (
      raw === null ||
      raw === undefined ||
      (typeof raw === 'string' && !raw.trim())
    ) {
      return null;
    }

    const number = typeof raw === 'number' ? raw : Number(raw);
    return Number.isFinite(number) ? number : null;
  }

  private asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {};
  }

  private flattenEvidence(
    record: Record<string, unknown>,
    prefix = '',
  ): QualityEvidenceItem[] {
    const items: QualityEvidenceItem[] = [];

    for (const [key, value] of Object.entries(record)) {
      const label = prefix
        ? `${prefix} / ${this.titleFromKey(key)}`
        : this.titleFromKey(key);

      if (value === null || value === undefined) {
        items.push({ label, value: 'Not available' });
      } else if (Array.isArray(value)) {
        items.push({
          label,
          value: value.map((item) => this.formatValue(item, key)).join(', ') || 'No recorded values',
        });
      } else if (typeof value === 'object') {
        const nested = this.asRecord(value);
        const nestedItems = this.flattenEvidence(nested, label);
        if (nestedItems.length) {
          items.push(...nestedItems);
        } else {
          items.push({ label, value: 'No recorded details' });
        }
      } else {
        items.push({ label, value: this.formatValue(value, key) });
      }
    }

    return items;
  }

  private formatValue(value: unknown, key?: string): string {
    if (value === null || value === undefined) {
      return 'Not available';
    }
    if (typeof value === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) {
        return 'Not available';
      }

      const percentageMetrics = new Set([
        'fidelity_rate',
        'missing_rate',
        'category_coverage',
        'expected_probability',
        'observed_probability',
        'absolute_probability_difference',
        'maximum_absolute_probability_difference',
      ]);

      if (key && percentageMetrics.has(key)) {
        return `${(value * 100).toFixed(1)}%`;
      }

      return value.toLocaleString('en-US');
    }
    if (typeof value === 'string') {
      return value || 'Empty';
    }
    return String(value);
  }

  private titleFromKey(key: string): string {
    return key
      .replaceAll('_', ' ')
      .replace(/\b\w/g, (character) => character.toUpperCase());
  }
}
