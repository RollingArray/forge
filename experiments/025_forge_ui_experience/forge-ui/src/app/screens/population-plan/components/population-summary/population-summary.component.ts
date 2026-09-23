import { DecimalPipe } from '@angular/common';

import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

export interface PopulationSummaryItem {
  readonly label: string;
  readonly value: number | string;
  readonly icon: string;
}

@Component({
  selector: 'app-population-summary',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DecimalPipe],
  templateUrl: './population-summary.component.html',
  styleUrl: './population-summary.component.css',
})
export class PopulationSummaryComponent {
  readonly items =
    input<readonly PopulationSummaryItem[]>([]);
}
