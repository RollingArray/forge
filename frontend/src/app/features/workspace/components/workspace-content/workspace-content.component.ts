/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: workspace-content.component.ts
 * Purpose: Defines the workspace content Workspace component.
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
  output,
} from '@angular/core';

import { Metric } from '../../../../core/interfaces/metric.interface';
import { DataModel } from '../../../../core/interfaces/data-model.interface';
import { Template } from '../../../../core/interfaces/template.interface';

import { MetricsComponent } from '../metrics/metrics.component';
import { RecentDataModelsComponent } from '../recent-data-models/recent-data-models.component';
import { TemplatesComponent } from '../templates/templates.component';

@Component({
  selector: 'app-workspace-content',
  standalone: true,
  imports: [
    MetricsComponent,
    RecentDataModelsComponent,
    TemplatesComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workspace-content.component.html',
  styleUrl: './workspace-content.component.css',
})
export class WorkspaceContentComponent {
  readonly metrics = input.required<Metric[]>();
  readonly dataModels = input.required<DataModel[]>();
  readonly templates = input.required<Template[]>();

  readonly selectedDataModel = input<DataModel | null>(null);

  readonly newDataModel = output<void>();
  readonly dataModelSelected = output<DataModel>();
  readonly templateSelected = output<string>();
}
