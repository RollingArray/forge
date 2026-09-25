/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: metrics.component.ts
 * Purpose: Defines the metrics Workspace component.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { Metric } from '../../../../core/interfaces/metric.interface';
import { MetricCardComponent } from '../metric-card/metric-card.component';

@Component({
  selector: 'app-workspace-metrics',
  standalone: true,
  imports: [MetricCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './metrics.component.html',
  styleUrl: './metrics.component.css',
})
export class MetricsComponent {
  readonly metrics = input.required<Metric[]>();
}
