import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import {
  GenerationQualityMetric,
  GenerationValidationMetric,
} from '../../models/generate.models';

@Component({
  selector: 'app-quality-summary',
  standalone: true,
  templateUrl: './quality-summary.component.html',
  styleUrl: './quality-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QualitySummaryComponent {
  readonly quality =
    input.required<readonly GenerationQualityMetric[]>();

  readonly validation =
    input.required<readonly GenerationValidationMetric[]>();
}
