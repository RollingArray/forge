import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';

import { SidebarComponent } from '../home/components/sidebar/sidebar.component';
import { StudioHeaderComponent } from '../model-studio/components/studio-header/studio-header.component';
import { WorkflowPageHeaderComponent } from '../../shared/components/workflow-page-header/workflow-page-header.component';

import { ForgeNavigationService } from '../../core/navigation/forge-navigation.service';

import {
  StudioStep,
} from '../model-studio/models/model-studio.models';

import {
  ResultsArtifact,
  ResultsViewModel,
} from './models/results.models';

import { ResultsDataService } from './services/results-data.service';
import { ResultsAdapterService } from './services/results-adapter.service';

import { GeneratedDatasetComponent } from './components/generated-dataset/generated-dataset.component';
import { DatasetActionsComponent } from './components/dataset-actions/dataset-actions.component';
import { OutputArtifactsComponent } from './components/output-artifacts/output-artifacts.component';
import { NextStepsComponent } from './components/next-steps/next-steps.component';
import { WorkflowActionBarComponent } from '../../shared/components/workflow-action-bar/workflow-action-bar.component';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [
    SidebarComponent,
    StudioHeaderComponent,
    WorkflowPageHeaderComponent,
    GeneratedDatasetComponent,
    DatasetActionsComponent,
    OutputArtifactsComponent,
    NextStepsComponent,
    WorkflowActionBarComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './results.component.html',
  styleUrl: './results.component.css',
})
export class ResultsComponent {
  private readonly navigation =
    inject(ForgeNavigationService);

  private readonly dataService =
    inject(ResultsDataService);

  private readonly adapter =
    inject(ResultsAdapterService);

  readonly steps = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ] as const;

  readonly activeStep =
    signal<StudioStep>('results');

  readonly data =
    signal<ResultsViewModel | null>(null);

  readonly isLoading =
    signal(true);

  readonly loadError =
    signal<string | null>(null);

  readonly artifacts =
    computed<readonly ResultsArtifact[]>(() => [
      {
        type: 'entity-files',
        title: 'Entity CSV Files',
        description:
          `${this.data()?.generatedEntityFiles ?? 0} CSV files • ${this.data()?.totalRecords.toLocaleString() ?? 0} records`,
        available: true,
      },
      {
        type: 'quality',
        title: 'Quality Report (JSON)',
        description:
          'Data quality assessment results',
        fileName:
          'quality.json',
        available:
          this.data()?.qualityReportAvailable ?? false,
      },
      {
        type: 'validation',
        title: 'Validation Report (JSON)',
        description:
          'Detailed validation results',
        fileName:
          'validation.json',
        available:
          this.data()?.validationReportAvailable ?? false,
      },
    ]);

  constructor() {
    this.loadData();
  }

  selectStep(step: StudioStep): void {
    this.navigation.navigateToStep(step);
  }

  viewInGenerate(): void {
    this.navigation.navigateToStep('generate');
  }

  createNewGeneration(): void {
    this.navigation.navigateToStep('population');
  }

  returnToModelStudio(): void {
    this.navigation.navigateToStep('model');
  }

  goBackToGenerate(): void {
    this.navigation.navigateToStep('generate');
  }

  startNewGeneration(): void {
    this.navigation.navigateToStep('population');
  }

  exploreDataset(): void {
    console.info(
      '[FORGE Results] dataset exploration requested',
    );
  }

  exportManifest(): void {
    const result = this.data();

    if (!result) {
      return;
    }

    const manifest = {
      job_id: result.jobId,
      status: result.status,
      updated_at: result.updatedAt,
      entities: result.entities.map(
        entity => ({
          entity: entity.name,
          records_generated:
            entity.recordsGenerated,
          output_file:
            entity.outputFile,
        }),
      ),
    };

    const blob = new Blob(
      [
        JSON.stringify(
          manifest,
          null,
          2,
        ),
      ],
      {
        type: 'application/json',
      },
    );

    const url =
      URL.createObjectURL(blob);

    const anchor =
      document.createElement('a');

    anchor.href = url;
    anchor.download =
      `${result.jobId}_manifest.json`;

    anchor.click();

    URL.revokeObjectURL(url);
  }

  downloadDataset(): void {
    console.info(
      '[FORGE Results] dataset package requested',
    );
  }

  downloadArtifact(
    artifact: ResultsArtifact,
  ): void {
    if (!artifact.fileName) {
      console.info(
        '[FORGE Results] artifact download requested:',
        artifact.title,
      );

      return;
    }

    const anchor =
      document.createElement('a');

    anchor.href =
      `/forge-data/generation/${artifact.fileName}`;

    anchor.download =
      artifact.fileName;

    anchor.click();
  }

  private async loadData(): Promise<void> {
    this.isLoading.set(true);
    this.loadError.set(null);

    try {
      const artifacts =
        await this.dataService.loadPromise();

      this.data.set(
        this.adapter.adapt(
          artifacts.checkpoint,
          artifacts.quality,
          artifacts.validation,
        ),
      );
    } catch (error) {
      console.error(
        '[FORGE Results] load failed',
        error,
      );

      this.loadError.set(
        error instanceof Error
          ? error.message
          : 'Unable to load generation results.',
      );
    } finally {
      this.isLoading.set(false);
    }
  }
}
