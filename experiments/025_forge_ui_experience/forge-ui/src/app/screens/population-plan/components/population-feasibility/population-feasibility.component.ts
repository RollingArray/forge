import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {
  PopulationStatus,
} from '../../models/population-plan.models';

@Component({
  selector: 'app-population-feasibility',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './population-feasibility.component.html',
  styleUrl: './population-feasibility.component.css',
})
export class PopulationFeasibilityComponent {
  readonly status =
    input<PopulationStatus>('FEASIBLE');

  readonly title =
    input('Population plan is feasible');

  readonly message =
    input(
      'All populations can be generated within the derived feasibility bounds.',
    );

  readonly icon = computed(() => {
    switch (this.status()) {
      case 'INFEASIBLE':
        return 'error';

      case 'WARNING':
        return 'warning';

      default:
        return 'check_circle';
    }
  });
}
