import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { SidebarComponent } from '../home/components/sidebar/sidebar.component';
import { StudioHeaderComponent } from '../model-studio/components/studio-header/studio-header.component';
import { WorkflowActionBarComponent } from '../../shared/components/workflow-action-bar/workflow-action-bar.component';
import { WorkflowPageHeaderComponent } from '../../shared/components/workflow-page-header/workflow-page-header.component';

import { ForgeNavigationService } from '../../core/navigation/forge-navigation.service';

import { StudioStep } from '../model-studio/models/model-studio.models';

import { ValidationViewModel } from './models/validate.models';

import { ValidationDataService } from './services/validation-data.service';
import { SpecificationValidationService } from './services/specification-validation.service';

import { ValidationSummaryComponent } from './components/validation-summary/validation-summary.component';
import { ValidationResultsComponent } from './components/validation-results/validation-results.component';
import { EntityValidationComponent } from './components/entity-validation/entity-validation.component';

@Component({
  selector: 'app-validate',
  standalone: true,
  imports: [
    SidebarComponent,
    StudioHeaderComponent,
    WorkflowActionBarComponent,
    WorkflowPageHeaderComponent,
    ValidationSummaryComponent,
    ValidationResultsComponent,
    EntityValidationComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './validate.component.html',
  styleUrl: './validate.component.css',
})
export class ValidateComponent {
  readonly navigation = inject(ForgeNavigationService);

  private readonly dataService = inject(ValidationDataService);

  private readonly validator = inject(SpecificationValidationService);

  readonly steps = [
    {
      id: 'model',
      number: 1,
      label: 'Model',
    },
    {
      id: 'validate',
      number: 2,
      label: 'Validate',
    },
    {
      id: 'population',
      number: 3,
      label: 'Population',
    },
    {
      id: 'generate',
      number: 4,
      label: 'Generate',
    },
    {
      id: 'results',
      number: 5,
      label: 'Results',
    },
  ] as const;

  readonly activeStep = signal<StudioStep>('validate');

  readonly data = signal<ValidationViewModel | null>(null);

  readonly isLoading = signal(true);

  readonly loadError = signal<string | null>(null);

  constructor() {
    this.loadData();
  }

  selectStep(step: StudioStep): void {
    this.navigation.navigateToStep(step);
  }

  viewSpecification(): void {
    this.navigation.navigateToStep('model');
  }

  goBack(): void {
    this.navigation.navigateToStep('model');
  }

  continueToPopulation(): void {
    console.log('[FORGE Validate] Navigating to Population Plan');
    this.navigation.navigateToStep('population');
  }

  private async loadData(): Promise<void> {
    this.isLoading.set(true);
    this.loadError.set(null);

    try {
      const specification = await this.dataService.load();

      this.data.set(this.validator.validate(specification));
    } catch (error) {
      console.error('[FORGE Validate] load failed', error);

      this.loadError.set(error instanceof Error ? error.message : 'Unable to load specification.');
    } finally {
      this.isLoading.set(false);
    }
  }
}
