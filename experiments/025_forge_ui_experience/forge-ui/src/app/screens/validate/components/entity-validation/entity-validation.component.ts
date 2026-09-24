import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { ValidationEntity } from '../../models/validate.models';

@Component({
  selector: 'app-entity-validation',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-validation.component.html',
  styleUrl: './entity-validation.component.css',
})
export class EntityValidationComponent {
  readonly entities =
    input.required<readonly ValidationEntity[]>();
}
