import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { Metric } from '../../models/home.models';
import { MetricCardComponent } from '../metric-card/metric-card.component';

@Component({
  selector: 'app-home-metrics',
  standalone: true,
  imports: [MetricCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './metrics.component.html',
  styleUrl: './metrics.component.css',
})
export class MetricsComponent {
  readonly metrics = input.required<Metric[]>();
}
