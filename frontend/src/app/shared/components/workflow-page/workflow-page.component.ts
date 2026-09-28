import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import {
  WorkflowStep,
  WorkflowStepItem,
  WorkflowStepperComponent,
} from '../workflow-stepper/workflow-stepper.component';
import { WorkflowActionBarComponent } from '../workflow-action-bar/workflow-action-bar.component';
import { WorkflowPageHeaderComponent } from '../workflow-page-header/workflow-page-header.component';
import { WorkflowContentComponent } from '../workflow-content/workflow-content.component';

@Component({
  selector: 'app-workflow-page',
  standalone: true,
  imports: [
    WorkflowStepperComponent,
    WorkflowPageHeaderComponent,
    WorkflowContentComponent,
    WorkflowActionBarComponent,
  ],
  templateUrl: './workflow-page.component.html',
  styleUrl: './workflow-page.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkflowPageComponent {
  readonly steps = input.required<readonly WorkflowStepItem[]>();
  readonly activeStep = input.required<WorkflowStep>();

  readonly pageIcon = input.required<string>();
  readonly pageTitle = input.required<string>();
  readonly pageDescription = input.required<string>();
  readonly progressLabel = input.required<string>();

  readonly actionBarIcon = input('fact_check');
  readonly actionBarTitle = input.required<string>();
  readonly actionBarDescription = input.required<string>();

  readonly secondaryLabel = input('');
  readonly secondaryIcon = input('arrow_back');

  readonly primaryLabel = input.required<string>();
  readonly primaryIcon = input('arrow_forward');
  readonly primaryDisabled = input(false);

  readonly stepSelected = output<WorkflowStep>();
  readonly secondaryAction = output<void>();
  readonly primaryAction = output<void>();
}
