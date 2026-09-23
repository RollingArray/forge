import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { ForgeNavigationService } from '../../core/navigation/forge-navigation.service';

import { SidebarComponent } from '../home/components/sidebar/sidebar.component';
import { StudioHeaderComponent } from '../model-studio/components/studio-header/studio-header.component';
import { WorkflowStepperComponent } from '../model-studio/components/workflow-stepper/workflow-stepper.component';
import { StudioStep } from '../model-studio/models/model-studio.models';

import { GenerationDataService } from './services/generation-data.service';
import { GenerationAdapterService } from './services/generation-adapter.service';
import { GenerationViewModel } from './models/generate.models';

import { GenerationSummaryComponent } from './components/generation-summary/generation-summary.component';
import { GenerationPipelineComponent } from './components/generation-pipeline/generation-pipeline.component';
import { EntityGenerationTableComponent } from './components/entity-generation-table/entity-generation-table.component';
import { CurrentActivityComponent } from './components/current-activity/current-activity.component';
import { GenerationLogsComponent } from './components/generation-logs/generation-logs.component';
import { QualitySummaryComponent } from './components/quality-summary/quality-summary.component';
import { CheckpointPanelComponent } from './components/checkpoint-panel/checkpoint-panel.component';

@Component({
  selector: 'app-generate',
  standalone: true,
  imports: [
    SidebarComponent,
    StudioHeaderComponent,
    WorkflowStepperComponent,
    GenerationSummaryComponent,
    GenerationPipelineComponent,
    EntityGenerationTableComponent,
    CurrentActivityComponent,
    GenerationLogsComponent,
    QualitySummaryComponent,
    CheckpointPanelComponent,
  ],
  templateUrl: './generate.component.html',
  styleUrl: './generate.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerateComponent {
  private readonly navigation = inject(ForgeNavigationService);
  private readonly dataService =
    inject(GenerationDataService);
  private readonly adapter =
    inject(GenerationAdapterService);

  readonly steps = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ] as const;

  readonly activeStep =
    signal<StudioStep>('generate');

  readonly data =
    signal<GenerationViewModel | null>(null);

  readonly isLoading =
    signal(true);

  readonly loadError =
    signal<string | null>(null);

  readonly isCompleted =
    computed(
      () => this.data()?.status === 'COMPLETED',
    );

  constructor() {
    this.loadData();
  }

  selectStep(step: StudioStep): void {
    this.navigation.navigateToStep(step);
  }

  private async loadData(): Promise<void> {
    this.isLoading.set(true);
    this.loadError.set(null);

    try {
      const artifacts =
        await this.dataService.load();

      this.data.set(
        this.adapter.adapt(artifacts),
      );
    } catch (error) {
      console.error(
        '[FORGE Generation] load failed',
        error,
      );

      this.loadError.set(
        error instanceof Error
          ? error.message
          : 'Unable to load generation artifacts.',
      );
    } finally {
      this.isLoading.set(false);
    }
  }
}
