/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: help-card.component.ts
 * Purpose: Defines the help card Workspace component.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  output,
} from '@angular/core';

@Component({
  selector: 'app-help-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './help-card.component.html',
  styleUrl: './help-card.component.css',
})
export class HelpCardComponent {
  readonly actionSelected = output<string>();

  openDocumentation(): void {
    this.actionSelected.emit('documentation');
  }
}
