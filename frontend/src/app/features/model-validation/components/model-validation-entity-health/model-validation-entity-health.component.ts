import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { SpecificationValidationResult } from '../../../../core/interfaces/specification-validation.interface';

import { ModelValidationEntityChartComponent } from '../model-validation-entity-chart/model-validation-entity-chart.component';
import { ModelValidationStatusChartComponent } from '../model-validation-status-chart/model-validation-status-chart.component';
import { ModelValidationEntityTableComponent } from '../model-validation-entity-table/model-validation-entity-table.component';

@Component({
  selector: 'app-model-validation-entity-health',
  standalone: true,
  imports: [
    ModelValidationEntityChartComponent,
    ModelValidationStatusChartComponent,
    ModelValidationEntityTableComponent,
  ],
  templateUrl: './model-validation-entity-health.component.html',
  styleUrl: './model-validation-entity-health.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelValidationEntityHealthComponent {
  readonly validation = input.required<SpecificationValidationResult>();
}
