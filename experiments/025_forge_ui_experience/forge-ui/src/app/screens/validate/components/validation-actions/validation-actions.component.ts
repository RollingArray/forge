import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

@Component({
  selector: 'app-validation-actions',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './validation-actions.component.html',
  styleUrl: './validation-actions.component.css',
})
export class ValidationActionsComponent {
  readonly canContinue =
    input(false);

  readonly back =
    output<void>();

  readonly continue =
    output<void>();
}
