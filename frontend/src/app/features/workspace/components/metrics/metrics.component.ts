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
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';

@Component({
  selector: 'app-workspace-metrics',
  standalone: true,
  imports: [MetricGridComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './metrics.component.html',
  styleUrl: './metrics.component.css',
})
export class MetricsComponent {
  readonly metrics = input.required<Metric[]>();

  readonly metricCards = () =>
    this.metrics().map((metric): MetricCardData => ({
      label: metric.label,
      value: metric.value,
      description: metric.supportingText,
      icon: metric.icon,
    }));
}
