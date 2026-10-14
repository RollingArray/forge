/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: confirmation-dialog.component.ts
 * Purpose: Reusable confirmation dialog for destructive and other decisions.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormDialogComponent } from '../form-dialog/form-dialog.component';

export type ConfirmationSeverity = 'danger' | 'warning' | 'info' | 'success';

@Component({
  selector: 'app-confirmation-dialog',
  standalone: true,
  imports: [FormDialogComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './confirmation-dialog.component.html',
  styleUrl: './confirmation-dialog.component.css',
})
export class ConfirmationDialogComponent {
  readonly title = input.required<string>();
  readonly message = input.required<string>();
  readonly icon = input<string>('help');
  readonly severity = input<ConfirmationSeverity>('warning');
  readonly confirmLabel = input<string>('Confirm');
  readonly cancelLabel = input<string>('Cancel');
  readonly context = input<string>('');
  readonly subject = input<string>('');
  readonly width = input<string>('520px');
  readonly busy = input<boolean>(false);
  readonly error = input<string | null>(null);

  readonly confirmed = output<void>();
  readonly cancelled = output<void>();

  confirm(): void {
    if (!this.busy()) {
      this.confirmed.emit();
    }
  }

  cancel(): void {
    if (!this.busy()) {
      this.cancelled.emit();
    }
  }
}
