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
} from '../../../screens/model-studio/models/model-studio.models';

@Component({
  selector: 'app-workflow-page-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workflow-page-header.component.html',
  styleUrl: './workflow-page-header.component.css',
})
export class WorkflowPageHeaderComponent {
  readonly currentStep = input.required<StudioStep>();
  readonly breadcrumbLabel = input.required<string>();
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  readonly icon = input.required<string>();

  readonly steps = input.required<readonly StudioStepItem[]>();

  readonly stepSelected = output<StudioStep>();

  readonly currentStepNumber = computed(() => {
    const step = this.steps().find(
      (item) => item.id === this.currentStep(),
    );

    return step?.number ?? 1;
  });

  readonly stepProgressLabel = computed(
    () => `${this.currentStepNumber()} of ${this.steps().length} steps`,
  );

  isCompleted(stepNumber: number): boolean {
    return stepNumber < this.currentStepNumber();
  }

  selectStep(step: StudioStep): void {
    this.stepSelected.emit(step);
  }
}
