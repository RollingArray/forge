import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { forkJoin } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';

import { WorkflowPageHeaderComponent } from '../../shared/components/workflow-page-header/workflow-page-header.component';
import { WorkflowContentComponent } from '../../shared/components/workflow-content/workflow-content.component';
import { WorkflowActionBarComponent } from '../../shared/components/workflow-action-bar/workflow-action-bar.component';
import { WorkspaceSimpleTableComponent } from '../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkspaceSimpleTableColumn } from '../../shared/components/workspace-simple-table/workspace-simple-table.models';
import { SpecificationService } from '../../core/services/specification.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  SpecificationImportApplyRequest,
  SpecificationImportCsv,
  SpecificationImportPreviewResponse,
} from '../../core/interfaces/specification-import.interface';

type CsvSectionKey =
  | 'entities'
  | 'fields_and_keys'
  | 'foreign_keys'
  | 'relationships'
  | 'constraints';

interface CsvSectionDefinition {
  key: CsvSectionKey;
  label: string;
  description: string;
  header: string;
}

interface CsvPreviewRow {
  rowId: number;
  [key: string]: string | number;
}

interface CsvParsePreview {
  headers: string[];
  rows: CsvPreviewRow[];
  error: string | null;
}

@Component({
  selector: 'app-specification-wizard',
  standalone: true,
  imports: [
    WorkflowPageHeaderComponent,
    WorkflowContentComponent,
    WorkflowActionBarComponent,
    WorkspaceSimpleTableComponent,
  ],
  templateUrl: './specification-wizard.component.html',
  styleUrl: './specification-wizard.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SpecificationWizardComponent {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly specificationService = inject(SpecificationService);
  private readonly notificationService = inject(NotificationService);

  readonly dataModelId = this.route.snapshot.paramMap.get('dataModelId') ?? '';

  readonly sections: readonly CsvSectionDefinition[] = [
    {
      key: 'entities',
      label: 'Entities',
      description: 'Define entities and their requested populations.',
      header: 'entity,description,population_count,population_scaling',
    },
    {
      key: 'fields_and_keys',
      label: 'Fields & Keys',
      description: 'Define fields, types, identities, and generation rules.',
      header: 'entity,field,type,identity_position,identity_strategy,generation_strategy,distribution,generator,minimum,maximum,minimum_length,maximum_length,character_set,pattern,semantic_description,semantic_mode,values',
    },
    {
      key: 'foreign_keys',
      label: 'Foreign Keys',
      description: 'Map source fields to the identity of a target entity.',
      header: 'source_entity,source_fields,target_entity',
    },
    {
      key: 'relationships',
      label: 'Relationships',
      description: 'Describe relationship cardinality and participation.',
      header: 'source_entity,target_entity,type,source_participation,target_participation',
    },
    {
      key: 'constraints',
      label: 'Constraints',
      description: 'Add field-level business constraints.',
      header: 'entity,field,operator,value',
    },
  ];

  readonly activeSection = signal<CsvSectionKey>('entities');

  readonly csvText = signal<SpecificationImportCsv>({
    entities: '',
    fields_and_keys: '',
    foreign_keys: '',
    relationships: '',
    constraints: '',
  });

  readonly previewInProgress = signal(false);
  readonly previewError = signal<string | null>(null);
  readonly previewResponse =
    signal<SpecificationImportPreviewResponse | null>(null);
  readonly previewedCsv = signal<SpecificationImportCsv | null>(null);
  readonly applyInProgress = signal(false);

  readonly activeSectionDefinition = computed(
    () =>
      this.sections.find((section) => section.key === this.activeSection()) ??
      this.sections[0],
  );

  readonly activeCsv = computed(
    () => this.csvText()[this.activeSection()],
  );

  readonly activeParsePreview = computed(
    () => this.parseCsv(this.activeCsv()),
  );

  readonly parseIssues = computed(() =>
    this.sections
      .map((section) => ({
        label: section.label,
        error: this.parseCsv(this.csvText()[section.key]).error,
      }))
      .filter(
        (item): item is { label: string; error: string } =>
          item.error !== null,
      ),
  );

  readonly previewColumns = computed<
    readonly WorkspaceSimpleTableColumn<CsvPreviewRow>[]
  >(() =>
    this.activeParsePreview().headers.map((header, index) => ({
      key: `column${index}` as keyof CsvPreviewRow,
      label: header,
      width: 'minmax(150px, 1fr)',
    })),
  );

  readonly previewRows = computed(
    () => this.activeParsePreview().rows,
  );

  readonly hasCsvContent = computed(() =>
    Object.values(this.csvText()).some((value) => value.trim().length > 0),
  );

  readonly canPreview = computed(
    () =>
      this.hasCsvContent() &&
      this.parseIssues().length === 0 &&
      !this.previewInProgress(),
  );

  readonly canApply = computed(() => {
    const response = this.previewResponse();
    const snapshot = this.previewedCsv();

    return Boolean(
      response &&
      response.can_apply &&
      response.conflicts.length === 0 &&
      response.issues.length === 0 &&
      snapshot &&
      JSON.stringify(snapshot) === JSON.stringify(this.csvText()) &&
      !this.previewInProgress() &&
      !this.applyInProgress(),
    );
  });

  readonly previewSummary = computed(() => {
    const summary = this.previewResponse()?.summary;
    return summary ? Object.entries(summary) : [];
  });

  private readonly sampleFiles: Record<CsvSectionKey, string> = {
    entities: '01_entities.csv',
    fields_and_keys: '02_fields_and_keys.csv',
    foreign_keys: '03_foreign_keys.csv',
    relationships: '04_relationships.csv',
    constraints: '05_constraints.csv',
  };

  loadAerospaceSample(): void {
    const base = '/assets/forge-samples/aerospace/';

    forkJoin({
      entities: this.http.get(`${base}${this.sampleFiles.entities}`, { responseType: 'text' }),
      fields_and_keys: this.http.get(`${base}${this.sampleFiles.fields_and_keys}`, { responseType: 'text' }),
      foreign_keys: this.http.get(`${base}${this.sampleFiles.foreign_keys}`, { responseType: 'text' }),
      relationships: this.http.get(`${base}${this.sampleFiles.relationships}`, { responseType: 'text' }),
      constraints: this.http.get(`${base}${this.sampleFiles.constraints}`, { responseType: 'text' }),
    }).subscribe({
      next: (csv) => {
        this.csvText.set(csv);
        this.activeSection.set('entities');
        this.resetPreviewState();
        this.notificationService.success(
          'Aerospace sample loaded',
          'All five sections are populated. Review the CSV and run Preview to validate it against this Data Model.',
        );
      },
      error: (error: unknown) => {
        console.error('[FORGE Specification Wizard] Failed to load aerospace sample:', error);
        this.previewError.set(
          'The aerospace sample files could not be loaded. Check that the sample assets are available.',
        );
        this.notificationService.error(
          'Sample loading failed',
          'FORGE could not load all five aerospace CSV files.',
        );
      },
    });
  }

  loadActiveSectionSample(): void {
    const section = this.activeSection();
    const file = this.sampleFiles[section];
    const url = `/assets/forge-samples/aerospace/${file}`;

    this.http.get(url, { responseType: 'text' }).subscribe({
      next: (content) => {
        this.setSectionCsv(section, content);
        this.notificationService.success(
          `${this.activeSectionDefinition().label} sample loaded`,
          'The active section has been replaced. Review it before running Preview.',
        );
      },
      error: (error: unknown) => {
        console.error('[FORGE Specification Wizard] Failed to load section sample:', error);
        this.previewError.set(
          `The sample for ${this.activeSectionDefinition().label} could not be loaded.`,
        );
        this.notificationService.error('Sample loading failed', 'The section sample could not be loaded.');
      },
    });
  }

  private setSectionCsv(section: CsvSectionKey, content: string): void {
    this.csvText.update((current) => ({
      ...current,
      [section]: content,
    }));
    this.resetPreviewState();
  }

  private resetPreviewState(): void {
    this.previewResponse.set(null);
    this.previewedCsv.set(null);
    this.previewError.set(null);
  }

  selectSection(section: CsvSectionKey): void {
    this.activeSection.set(section);
  }

  updateCsv(event: Event): void {
    const target = event.target;
    if (!(target instanceof HTMLTextAreaElement)) {
      return;
    }

    const key = this.activeSection();
    this.setSectionCsv(key, target.value);
  }

  sectionHasContent(section: CsvSectionKey): boolean {
    return this.csvText()[section].trim().length > 0;
  }

  previewImport(): void {
    if (!this.dataModelId || !this.canPreview()) {
      return;
    }

    this.previewInProgress.set(true);
    this.previewError.set(null);
    this.previewResponse.set(null);
    this.previewedCsv.set(null);
    const csvSnapshot = { ...this.csvText() };

    this.specificationService
      .previewImport(this.dataModelId, csvSnapshot)
      .subscribe({
        next: (response) => {
          this.previewResponse.set(response);
          this.previewedCsv.set(csvSnapshot);
          this.previewInProgress.set(false);
        },
        error: (error: unknown) => {
          const detail =
            error instanceof HttpErrorResponse
              ? error.error?.detail
              : null;

          this.previewError.set(
            typeof detail === 'string'
              ? detail
              : detail
                ? JSON.stringify(detail)
                : 'FORGE could not preview this CSV import. Check the CSV content and try again.',
          );
          this.previewInProgress.set(false);
        },
      });
  }

  handlePrimaryAction(): void {
    if (this.canApply()) {
      this.applyImport();
      return;
    }

    this.previewImport();
  }

  applyImport(): void {
    const preview = this.previewResponse();
    const csvSnapshot = this.previewedCsv();

    if (!this.dataModelId || !preview || !csvSnapshot || !this.canApply()) {
      return;
    }

    const request: SpecificationImportApplyRequest = {
      base_revision: preview.base_revision,
      csv_digest: preview.csv_digest,
      csv: { ...csvSnapshot },
    };

    this.applyInProgress.set(true);
    this.previewError.set(null);

    this.specificationService
      .applyImport(this.dataModelId, request)
      .subscribe({
        next: (response) => {
          this.applyInProgress.set(false);
          const message = response.applied
            ? 'The CSV additions have been applied to the specification.'
            : 'The specification is up to date. No additional changes were required.';

          this.notificationService.success(
            'Specification import complete',
            message,
          );

          this.returnToModelStudio();
        },
        error: (error: unknown) => {
          this.applyInProgress.set(false);
          const status =
            error instanceof HttpErrorResponse ? error.status : null;
          const detail =
            error instanceof HttpErrorResponse
              ? error.error?.detail
              : null;

          this.previewError.set(
            status === 409
              ? 'The specification changed after this preview was created. Run Preview again before applying.'
              : typeof detail === 'string'
                ? detail
                : detail
                  ? JSON.stringify(detail)
                  : 'FORGE could not apply this CSV import. Review the preview and try again.',
          );

          this.notificationService.error(
            'Specification import failed',
            this.previewError() ?? 'The CSV import could not be applied.',
            status,
          );
        },
      });
  }

  formatFinding(finding: Record<string, unknown>): string {
    return Object.entries(finding)
      .map(([key, value]) => `${key}: ${String(value)}`)
      .join(' · ');
  }

  returnToModelStudio(): void {
    if (!this.dataModelId) {
      return;
    }

    void this.router.navigate([
      '/workspace',
      this.dataModelId,
      'model-studio',
    ]);
  }

  private parseCsv(source: string): CsvParsePreview {
    const text = source.replace(/^\uFEFF/, '');
    if (!text.trim()) {
      return { headers: [], rows: [], error: null };
    }

    const records: string[][] = [];
    let record: string[] = [];
    let field = '';
    let inQuotes = false;

    for (let index = 0; index < text.length; index += 1) {
      const character = text[index];

      if (inQuotes) {
        if (character === '"') {
          if (text[index + 1] === '"') {
            field += '"';
            index += 1;
          } else {
            inQuotes = false;
          }
        } else {
          field += character;
        }
        continue;
      }

      if (character === '"') {
        if (field.length > 0) {
          return {
            headers: [],
            rows: [],
            error: `Unexpected quote at character ${index + 1}.`,
          };
        }
        inQuotes = true;
      } else if (character === ',') {
        record.push(field);
        field = '';
      } else if (character === '\n' || character === '\r') {
        record.push(field);
        if (record.some((value) => value.trim().length > 0)) {
          records.push(record);
        }
        record = [];
        field = '';
        if (character === '\r' && text[index + 1] === '\n') {
          index += 1;
        }
      } else {
        field += character;
      }
    }

    if (inQuotes) {
      return {
        headers: [],
        rows: [],
        error: 'A quoted CSV value was not closed.',
      };
    }

    record.push(field);
    if (record.some((value) => value.trim().length > 0)) {
      records.push(record);
    }

    if (records.length === 0) {
      return { headers: [], rows: [], error: null };
    }

    const headers = records[0].map((value) => value.trim());
    if (headers.some((header) => !header)) {
      return {
        headers,
        rows: [],
        error: 'The CSV header row contains an empty column name.',
      };
    }

    if (new Set(headers).size !== headers.length) {
      return {
        headers,
        rows: [],
        error: 'The CSV header row contains duplicate column names.',
      };
    }

    const rows: CsvPreviewRow[] = [];
    for (let index = 1; index < records.length; index += 1) {
      const values = records[index];
      if (values.length !== headers.length) {
        return {
          headers,
          rows,
          error: `Row ${index + 1} has ${values.length} values; expected ${headers.length}.`,
        };
      }

      const row: CsvPreviewRow = { rowId: index };
      values.forEach((value, columnIndex) => {
        row[`column${columnIndex}`] = value;
      });
      rows.push(row);
    }

    return { headers, rows, error: null };
  }
}
