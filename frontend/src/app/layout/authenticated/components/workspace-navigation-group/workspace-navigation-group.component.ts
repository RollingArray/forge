import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

export interface WorkspaceNavigationItem {
  readonly label: string;
  readonly icon: string;
  readonly action: string;
  readonly availability?: 'available' | 'soon';
}

export interface WorkspaceNavigationGroup {
  readonly title: string;
  readonly icon: string;
  readonly items: readonly WorkspaceNavigationItem[];
}

@Component({
  selector: 'app-workspace-navigation-group',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workspace-navigation-group.component.html',
  styleUrl: './workspace-navigation-group.component.css',
})
export class WorkspaceNavigationGroupComponent {
  readonly group = input.required<WorkspaceNavigationGroup>();
  readonly activeAction = input<string | null>(null);
  readonly selected = output<string>();

  selectItem(item: WorkspaceNavigationItem): void {
    console.debug('[EXECUTION SELECTOR DEBUG] Navigation click', {
      label: item.label,
      action: item.action,
      availability: item.availability,
    });

    if (item.availability === 'soon' || !item.action) {
      console.debug('[EXECUTION SELECTOR DEBUG] Click ignored');
      return;
    }

    console.debug('[EXECUTION SELECTOR DEBUG] Emitting action', item.action);
    this.selected.emit(item.action);
  }
}
