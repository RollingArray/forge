/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: workflow-action-bar.component.ts
 * Purpose: Provides the reusable workflow action bar for FORGE workflow pages.
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
import { ForgeButtonComponent } from '../forge-button/forge-button.component';

@Component({
  selector: 'app-workflow-action-bar',
  standalone: true,
  imports: [ForgeButtonComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workflow-action-bar.component.html',
  styleUrl: './workflow-action-bar.component.css',
})
export class WorkflowActionBarComponent {
  readonly icon = input('fact_check');
  readonly title = input.required<string>();
  readonly description = input.required<string>();

  readonly secondaryLabel = input('');
  readonly secondaryIcon = input('arrow_back');

  readonly contextualActionLabel = input('');
  readonly contextualActionIcon = input('pause');
  readonly contextualActionDisabled = input(false);

  readonly primaryLabel = input.required<string>();
  readonly primaryIcon = input('arrow_forward');
  readonly primaryDisabled = input(false);

  readonly secondaryAction = output<void>();
  readonly contextualAction = output<void>();
  readonly primaryAction = output<void>();

  handleSecondaryAction(): void {
    this.secondaryAction.emit();
  }

  handleContextualAction(): void {
    if (this.contextualActionDisabled()) {
      return;
    }

    this.contextualAction.emit();
  }

  handlePrimaryAction(): void {
    if (this.primaryDisabled()) {
      return;
    }

    this.primaryAction.emit();
  }
}
