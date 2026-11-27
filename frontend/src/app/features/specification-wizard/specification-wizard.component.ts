import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import {
  HttpClient,
  HttpContext,
  HttpErrorResponse,
} from '@angular/common/http';
import { forkJoin } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';

import { WorkflowPageHeaderComponent } from '../../shared/components/workflow-page-header/workflow-page-header.component';
import { WorkflowContentComponent } from '../../shared/components/workflow-content/workflow-content.component';
import { WorkflowActionBarComponent } from '../../shared/components/workflow-action-bar/workflow-action-bar.component';
import { ForgeButtonComponent } from '../../shared/components/forge-button/forge-button.component';
import { WorkspaceSimpleTableComponent } from '../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkspaceSimpleTableColumn } from '../../shared/components/workspace-simple-table/workspace-simple-table.models';
import { SpecificationService } from '../../core/services/specification.service';
import { NotificationService } from '../../core/services/notification.service';
import { SpecificationReplacementCsv } from '../../core/interfaces/specification-replacement-csv.interface';
import { SpecificationReplacementPreviewResponse } from '../../core/interfaces/specification-replacement-preview-response.interface';

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
    ForgeButtonComponent,
    WorkspaceSimpleTableComponent,
  ],
  templateUrl: './specification-wizard.component.html',
  styleUrl: './specification-wizard.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SpecificationWizardComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly http = inject(HttpClient);

  private readonly sampleBase = '/assets/forge-samples/aerospace/';

  private readonly sampleFiles: Record<CsvSectionKey, string> = {
    entities: '01_entities.csv',
    fields_and_keys: '02_fields_and_keys.csv',
    foreign_keys: '03_foreign_keys.csv',
    relationships: '04_relationships.csv',
    constraints: '05_constraints.csv',
  };
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

  @ViewChild('replacementReview')
  private replacementReview?: ElementRef<HTMLElement>;

  readonly activeSection = signal<CsvSectionKey>('entities');

  private userModifiedCsv = false;

  readonly csvText = signal<SpecificationReplacementCsv>({
    entities: '',
    fields_and_keys: '',
    foreign_keys: '',
    relationships: '',
    constraints: '',
  });

  readonly previewInProgress = signal(false);
  readonly previewError = signal<string | null>(null);
  readonly previewResponse =
    signal<SpecificationReplacementPreviewResponse | null>(null);

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

  readonly previewSummary = computed(() => {
    const summary = this.previewResponse()?.summary;
    return summary ? Object.entries(summary) : [];
  });

  ngOnInit(): void {
    const navigationState =
      this.router.getCurrentNavigation()?.extras.state ?? history.state;
    const restoredCsv = navigationState?.['replacementCsv'] as
      | SpecificationReplacementCsv
      | undefined;

    const hasRestorableCsv =
      restoredCsv &&
      this.sections.every(
        (section) =>
          typeof restoredCsv[section.key] === 'string',
      );

    if (hasRestorableCsv) {
      this.csvText.set({ ...restoredCsv });
      this.activeSection.set('entities');
      this.resetPreviewState();
      return;
    }

    this.loadCurrentSpecification(false);
  }

  loadCurrentSpecification(showSuccessNotification = true): void {
    if (!this.dataModelId) {
      return;
    }

    this.previewError.set(null);

    this.specificationService
      .exportReplacement(this.dataModelId)
      .subscribe({
        next: (csv) => {
          if (!showSuccessNotification && this.userModifiedCsv) {
            return;
          }

          this.csvText.set(csv);
          this.activeSection.set('entities');
          this.resetPreviewState();
          if (showSuccessNotification) {
            this.notificationService.success(
              'Current specification loaded',
              'All five canonical CSV sections are ready for editing.',
            );
          }
        },
        error: (error: unknown) => {
          console.error(
            '[FORGE Specification Wizard] Export failed:',
            error,
          );

          const detail =
            error instanceof HttpErrorResponse
              ? error.error?.detail ?? error.error
              : error;

          const message =
            typeof detail === 'string'
              ? detail
              : detail
                ? JSON.stringify(detail, null, 2)
                : 'The current specification could not be exported.';

          this.previewError.set(message);

          this.notificationService.error(
            'Specification export failed',
            message,
          );
        },
      });
  }


  downloadTemplate(): void {
    const anchor = document.createElement('a');
    anchor.href = '/assets/forge-templates/forge-specification-template.zip';
    anchor.download = 'forge-specification-template.zip';
    anchor.click();
  }

  loadAerospaceSample(): void {
    this.loadAerospaceSampleSections();
  }

  loadActiveSectionSample(): void {
    this.loadAerospaceSampleSections(this.activeSection());
  }

  private loadAerospaceSampleSections(
    onlySection?: CsvSectionKey,
  ): void {
    this.userModifiedCsv = true;

    forkJoin({
      entities: this.http.get(
        `${this.sampleBase}${this.sampleFiles.entities}`,
        { responseType: 'text' },
      ),
      fields_and_keys: this.http.get(
        `${this.sampleBase}${this.sampleFiles.fields_and_keys}`,
        { responseType: 'text' },
      ),
      foreign_keys: this.http.get(
        `${this.sampleBase}${this.sampleFiles.foreign_keys}`,
        { responseType: 'text' },
      ),
      relationships: this.http.get(
        `${this.sampleBase}${this.sampleFiles.relationships}`,
        { responseType: 'text' },
      ),
      constraints: this.http.get(
        `${this.sampleBase}${this.sampleFiles.constraints}`,
        { responseType: 'text' },
      ),
    }).subscribe({
      next: (legacy) => {
        try {
          const converted = this.convertAerospaceSample(legacy);

          if (onlySection) {
            this.setSectionCsv(onlySection, converted[onlySection]);
            this.notificationService.success(
              'Aerospace sample loaded',
              `${onlySection} sample is ready for editing.`,
            );
          } else {
            this.csvText.set(converted);
            this.activeSection.set('entities');
            this.resetPreviewState();
            this.notificationService.success(
              'Aerospace sample loaded',
              'All five sample sections are ready for editing.',
            );
          }
        } catch (error) {
          console.error(
            '[FORGE Specification Wizard] Sample conversion failed:',
            error,
          );
          this.notificationService.error(
            'Sample loading failed',
            error instanceof Error
              ? error.message
              : 'The Aerospace sample could not be converted.',
          );
        }
      },
      error: (error: unknown) => {
        console.error(
          '[FORGE Specification Wizard] Sample loading failed:',
          error,
        );
        this.notificationService.error(
          'Sample loading failed',
          'The original Aerospace sample files could not be loaded.',
        );
      },
    });
  }

  private convertAerospaceSample(
    legacy: SpecificationReplacementCsv,
  ): SpecificationReplacementCsv {
    const parseRecords = (content: string): Record<string, string>[] => {
      const parsed = this.parseCsv(content);
      if (parsed.error) {
        throw new Error(parsed.error);
      }

      return parsed.rows.map((row) => {
        const record: Record<string, string> = {};
        parsed.headers.forEach((header, index) => {
          record[header] = String(row[`column${index}`] ?? '');
        });
        return record;
      });
    };

    const serialize = (
      headers: string[],
      records: Record<string, string>[],
    ): string => {
      const escape = (value: string): string => {
        if (/[",\r\n]/.test(value)) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      };

      return [
        headers.map(escape).join(','),
        ...records.map((record) =>
          headers.map((header) => escape(record[header] ?? '')).join(','),
        ),
      ].join('\n');
    };

    const entities = parseRecords(legacy.entities);
    const fields = parseRecords(legacy.fields_and_keys);
    const foreignKeys = parseRecords(legacy.foreign_keys);
    const relationships = parseRecords(legacy.relationships);
    const constraints = parseRecords(legacy.constraints);

    const fieldHeaders = this.sections
      .find((section) => section.key === 'fields_and_keys')!
      .header.split(',');

    return {
      entities: serialize(
        ['entity', 'description', 'population_count', 'population_scaling'],
        entities,
      ),
      fields_and_keys: serialize(fieldHeaders, fields),
      foreign_keys: serialize(
        ['source_entity', 'source_fields', 'target_entity'],
        foreignKeys,
      ),
      relationships: serialize(
        [
          'source_entity',
          'target_entity',
          'type',
          'source_participation',
          'target_participation',
        ],
        relationships,
      ),
      constraints: serialize(
        ['entity', 'field', 'operator', 'value'],
        constraints,
      ),
    };
  }

  downloadActiveCsv(): void {
    const section = this.activeSection();
    const content = this.csvText()[section];

    if (!content.trim()) {
      return;
    }

    const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');

    anchor.href = url;
    anchor.download = `${section}.csv`;
    anchor.click();

    URL.revokeObjectURL(url);
  }

  private setSectionCsv(section: CsvSectionKey, content: string): void {
    this.userModifiedCsv = true;

    this.csvText.update((current) => ({
      ...current,
      [section]: content,
    }));
    this.resetPreviewState();
  }

  private resetPreviewState(): void {
    this.previewResponse.set(null);
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

  previewReplacement(): void {
    if (!this.dataModelId || !this.canPreview()) {
      return;
    }

    this.previewInProgress.set(true);
    this.previewError.set(null);
    this.previewResponse.set(null);

    const csvSnapshot = { ...this.csvText() };

    this.specificationService
      .previewReplacement(this.dataModelId, csvSnapshot)
      .subscribe({
        next: (response) => {
          this.previewResponse.set(response);
          this.previewInProgress.set(false);

          if (!response.can_apply || response.issues.length > 0) {
            const issueCount = response.issues.length;

            this.notificationService.error(
              'CSV replacement needs attention',
              issueCount > 0
                ? `FORGE found ${issueCount} CSV conversion issue${issueCount === 1 ? '' : 's'}. Review the details below and correct the CSV before continuing.`
                : 'The replacement could not be prepared. Review the details below.',
            );

            requestAnimationFrame(() => {
              this.replacementReview?.nativeElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
              });

              this.replacementReview?.nativeElement.focus({
                preventScroll: true,
              });
            });

            return;
          }

          const request = {
            base_revision: response.base_revision,
            csv_digest: response.csv_digest,
            csv: csvSnapshot,
          };

          void this.router.navigate(
            ['/workspace', this.dataModelId, 'model-validation'],
            { state: { replacement: request } },
          );
        },
        error: (error: unknown) => {
          const detail =
            error instanceof HttpErrorResponse ? error.error?.detail : null;

          this.previewError.set(
            typeof detail === 'string'
              ? detail
              : detail
                ? JSON.stringify(detail)
                : 'FORGE could not preview this specification replacement.',
          );
          this.previewInProgress.set(false);
        },
      });
  }

  handlePrimaryAction(): void {
    this.previewReplacement();
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
