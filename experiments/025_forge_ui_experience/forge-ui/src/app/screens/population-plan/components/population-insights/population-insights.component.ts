import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import {
  PopulationInsight,
} from '../../models/population-plan.models';

@Component({
  selector: 'app-population-insights',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './population-insights.component.html',
  styleUrl: './population-insights.component.css',
})
export class PopulationInsightsComponent {
  readonly insights =
    input<readonly PopulationInsight[]>([]);
}
