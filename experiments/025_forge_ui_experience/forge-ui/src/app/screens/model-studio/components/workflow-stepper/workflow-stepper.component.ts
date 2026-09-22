import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import {
  StudioStep,
  StudioStepItem,
} from '../../models/model-studio.models';

@Component({
  selector: 'app-workflow-stepper',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workflow-stepper.component.html',
  styleUrl: './workflow-stepper.component.css',
})
export class WorkflowStepperComponent {
  readonly steps = input.required<readonly StudioStepItem[]>();
  readonly activeStep = input<StudioStep>('model');

  readonly stepSelected = output<StudioStep>();

  selectStep(step: StudioStep): void {
    this.stepSelected.emit(step);
  }
}
