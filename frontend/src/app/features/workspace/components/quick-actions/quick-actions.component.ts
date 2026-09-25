/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: quick-actions.component.ts
 * Purpose: Defines the quick actions Workspace component.
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

import { QuickAction } from '../../../../core/interfaces/quick-action.interface';

@Component({
  selector: 'app-quick-actions',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './quick-actions.component.html',
  styleUrl: './quick-actions.component.css',
})
export class QuickActionsComponent {
  readonly actionSelected = output<string>();

  readonly actions: QuickAction[] = [
    {
      label: 'New DataModel',
      icon: 'add_circle',
      action: 'new-dataModel',
    },
    {
      label: 'Import Model',
      icon: 'upload_file',
      action: 'import-model',
    },
    {
      label: 'Use Template',
      icon: 'dashboard_customize',
      action: 'use-template',
    },
    {
      label: 'Documentation',
      icon: 'menu_book',
      action: 'documentation',
    },
  ];

  selectAction(action: QuickAction): void {
    this.actionSelected.emit(action.action);
  }
}
