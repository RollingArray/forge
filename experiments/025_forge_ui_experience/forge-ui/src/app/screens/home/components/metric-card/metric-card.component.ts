import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { Metric } from '../../models/home.models';

@Component({
  selector: 'app-metric-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './metric-card.component.html',
  styleUrl: './metric-card.component.css',
})
export class MetricCardComponent {
  readonly metric = input.required<Metric>();
}
