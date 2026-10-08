import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { MetricCardComponent } from '../metric-card/metric-card.component';
import { MetricCardData } from './metric-card-data';

@Component({
  selector: 'app-metric-grid',
  standalone: true,
  imports: [MetricCardComponent],
  templateUrl: './metric-grid.component.html',
  styleUrl: './metric-grid.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MetricGridComponent {
  readonly columns = input.required<number>();
  readonly metrics = input.required<readonly MetricCardData[]>();
}
