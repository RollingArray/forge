/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: workspace-welcome-header.component.ts
 * Purpose: Defines the workspace welcome header Workspace component.
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
  selector: 'app-workspace-welcome-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workspace-welcome-header.component.html',
  styleUrl: './workspace-welcome-header.component.css',
})
export class WorkspaceWelcomeHeaderComponent {
  readonly newDataModel = output<void>();

  createDataModel(): void {
    this.newDataModel.emit();
  }
}
