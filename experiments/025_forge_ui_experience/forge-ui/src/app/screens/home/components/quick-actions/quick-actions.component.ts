import {
  ChangeDetectionStrategy,
  Component,
  output,
} from '@angular/core';

import { QuickAction } from '../../models/home.models';

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
      label: 'New Session',
      icon: 'add_circle',
      action: 'new-session',
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
