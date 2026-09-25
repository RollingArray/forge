/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: form-dialog.component.ts
 * Purpose: Provides the reusable FORGE modal shell for form-based workflows.
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

@Component({
  selector: 'app-form-dialog',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './form-dialog.component.html',
  styleUrl: './form-dialog.component.css',
})
export class FormDialogComponent {
  readonly title = input.required<string>();
  readonly subtitle = input<string>('');
  readonly icon = input<string>('edit');
  readonly closeLabel = input<string>('Close');
  readonly width = input<string>('520px');

  readonly closed = output<void>();

  close(): void {
    this.closed.emit();
  }

  stopPropagation(event: MouseEvent): void {
    event.stopPropagation();
  }
}
