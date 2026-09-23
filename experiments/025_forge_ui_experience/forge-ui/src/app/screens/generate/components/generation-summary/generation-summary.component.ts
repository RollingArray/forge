import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { GenerationViewModel } from '../../models/generate.models';

@Component({
  selector: 'app-generation-summary',
  standalone: true,
  templateUrl: './generation-summary.component.html',
  styleUrl: './generation-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationSummaryComponent {
  readonly data = input.required<GenerationViewModel>();

  formatNumber(value: number): string {
    return value.toLocaleString();
  }

  formatDuration(
    seconds: number | null,
  ): string {
    if (seconds === null) {
      return 'Unavailable';
    }

    const minutes =
      Math.floor(seconds / 60);

    const remaining =
      Math.floor(seconds % 60);

    return `${minutes.toString().padStart(2, '0')}:${remaining.toString().padStart(2, '0')}`;
  }

  formatRate(
    value: number | null,
  ): string {
    return value === null
      ? 'Unavailable'
      : value.toLocaleString(
          undefined,
          { maximumFractionDigits: 0 },
        );
  }
}
