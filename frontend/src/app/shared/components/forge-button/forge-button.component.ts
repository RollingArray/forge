export type ForgeButtonVariant = 'primary' | 'secondary';

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

@Component({
  selector: 'app-forge-button',
  standalone: true,
  templateUrl: './forge-button.component.html',
  styleUrl: './forge-button.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ForgeButtonComponent {
  readonly label = input.required<string>();
  readonly icon = input<string | null>(null);
  readonly disabled = input(false);
  readonly ariaLabel = input<string | null>(null);
  readonly title = input<string | null>(null);
  readonly variant = input<ForgeButtonVariant>('primary');

  readonly clicked = output<void>();
}
