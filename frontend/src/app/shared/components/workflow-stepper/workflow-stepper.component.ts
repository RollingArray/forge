import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

export type WorkflowStep =
  | 'model'
  | 'validate'
  | 'population'
  | 'generate'
  | 'results';

export interface WorkflowStepItem {
  id: WorkflowStep;
  number: number;
  label: string;
}

@Component({
  selector: 'app-workflow-stepper',
  standalone: true,
  templateUrl: './workflow-stepper.component.html',
  styleUrl: './workflow-stepper.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkflowStepperComponent {
  readonly steps = input.required<readonly WorkflowStepItem[]>();
  readonly activeStep = input.required<WorkflowStep>();

  readonly stepSelected = output<WorkflowStep>();

  isCompleted(stepNumber: number): boolean {
    const active = this.steps().find(
      (step) => step.id === this.activeStep(),
    );

    return !!active && stepNumber < active.number;
  }

  selectStep(step: WorkflowStep): void {
    this.stepSelected.emit(step);
  }
}
