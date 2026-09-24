import {
  ChangeDetectionStrategy,
  Component,
  computed,
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
  readonly steps =
    input.required<readonly StudioStepItem[]>();

  readonly activeStep =
    input<StudioStep>('model');

  readonly stepSelected =
    output<StudioStep>();

  private readonly stepOrder: readonly StudioStep[] = [
    'model',
    'validate',
    'population',
    'generate',
    'results',
  ];

  readonly activeStepNumber =
    computed(() => {
      const index =
        this.stepOrder.indexOf(
          this.activeStep(),
        );

      return index >= 0
        ? index + 1
        : 1;
    });

  isCompleted(
    stepNumber: number,
  ): boolean {
    return (
      stepNumber <
      this.activeStepNumber()
    );
  }

  selectStep(
    step: StudioStep,
  ): void {
    this.stepSelected.emit(step);
  }
}
