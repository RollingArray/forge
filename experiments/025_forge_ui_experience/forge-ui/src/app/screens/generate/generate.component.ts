import { ChangeDetectionStrategy, Component, signal } from '@angular/core';

import { SidebarComponent } from '../home/components/sidebar/sidebar.component';
import { StudioHeaderComponent } from '../model-studio/components/studio-header/studio-header.component';
import { WorkflowStepperComponent } from '../model-studio/components/workflow-stepper/workflow-stepper.component';

@Component({
  selector: 'app-generate',
  standalone: true,
  imports: [
    SidebarComponent,
    StudioHeaderComponent,
    WorkflowStepperComponent,
  ],
  templateUrl: './generate.component.html',
  styleUrl: './generate.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerateComponent {
  readonly activeStep = signal<'generate'>('generate');

  readonly steps = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ] as const;
}
