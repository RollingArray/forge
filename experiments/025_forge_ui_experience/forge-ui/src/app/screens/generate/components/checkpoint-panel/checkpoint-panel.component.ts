import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { GenerationViewModel } from '../../models/generate.models';

@Component({
  selector: 'app-checkpoint-panel',
  standalone: true,
  templateUrl: './checkpoint-panel.component.html',
  styleUrl: './checkpoint-panel.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckpointPanelComponent {
  readonly data =
    input.required<GenerationViewModel>();

  formatDate(value: string): string {
    return new Date(value).toLocaleString();
  }
}
