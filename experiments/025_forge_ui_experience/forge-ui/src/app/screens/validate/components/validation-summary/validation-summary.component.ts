import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import { ValidationViewModel } from '../../models/validate.models';

@Component({
  selector: 'app-validation-summary',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './validation-summary.component.html',
  styleUrl: './validation-summary.component.css',
})
export class ValidationSummaryComponent {
  readonly data =
    input.required<ValidationViewModel>();

  readonly passRate =
    computed(() => {
      const value =
        this.data().totalChecks > 0
          ? (
              this.data().passed /
              this.data().totalChecks
            ) * 100
          : 0;

      return Math.round(value);
    });
}
