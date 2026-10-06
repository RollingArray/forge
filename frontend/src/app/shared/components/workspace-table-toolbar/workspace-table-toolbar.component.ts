import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

export interface WorkspaceToolbarFilter {
  id: string;
  label: string;
  icon?: string;
  count?: number;
  active?: boolean;
  variant?: 'primary' | 'success' | 'warning' | 'danger';
}

export interface WorkspaceToolbarAction {
  id: string;
  icon: string;
  label?: string;
  variant?: 'default' | 'primary' | 'danger';
  disabled?: boolean;
  tooltip?: string;
}

@Component({
  selector: 'app-workspace-table-toolbar',
  standalone: true,
  templateUrl: './workspace-table-toolbar.component.html',
  styleUrl: './workspace-table-toolbar.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceTableToolbarComponent {
  readonly summaryIcon = input('description');
  readonly summary = input('');

  readonly filters = input<WorkspaceToolbarFilter[]>([]);

  readonly showSearch = input(false);
  readonly searchPlaceholder = input('Search...');
  readonly searchValue = input('');

  readonly actions = input<WorkspaceToolbarAction[]>([]);

  readonly searchValueChange = output<string>();
  readonly filterChange = output<string>();
  readonly action = output<string>();

  onSearch(value: string): void {
    this.searchValueChange.emit(value);
  }

  onFilterChange(filter: WorkspaceToolbarFilter): void {
    this.filterChange.emit(filter.id);
  }

  onAction(action: WorkspaceToolbarAction): void {
    if (action.disabled) {
      return;
    }

    this.action.emit(action.id);
  }
}
