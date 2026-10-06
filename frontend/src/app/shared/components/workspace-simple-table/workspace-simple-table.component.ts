import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { WorkspaceTableEmptyComponent } from '../workspace-table-empty/workspace-table-empty.component';
import { WorkspaceTableToolbarComponent } from '../workspace-table-toolbar/workspace-table-toolbar.component';
import {
  WorkspaceSimpleTableColumn,
} from './workspace-simple-table.models';

@Component({
  selector: 'app-workspace-simple-table',
  standalone: true,
  imports: [
    WorkspaceTableToolbarComponent,
    WorkspaceTableEmptyComponent,
  ],
  templateUrl: './workspace-simple-table.component.html',
  styleUrl: './workspace-simple-table.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceSimpleTableComponent<T extends object> {
  readonly columns =
    input.required<readonly WorkspaceSimpleTableColumn<T>[]>();

  readonly rows = input.required<readonly T[]>();

  readonly rowKey = input.required<keyof T>();

  readonly searchValue = input('');

  readonly showSearch = input(false);

  readonly searchPlaceholder = input('Search...');

  readonly emptyMessage = input('No records available.');

  readonly searchValueChange = output<string>();

  updateSearchValue(value: string): void {
    this.searchValueChange.emit(value);
  }

  getCellValue(row: T, column: WorkspaceSimpleTableColumn<T>): unknown {
    return row[column.key];
  }

  getRowKey(row: T): string | number {
    return row[this.rowKey()] as string | number;
  }

  isErrorCount(column: WorkspaceSimpleTableColumn<T>, row: T): boolean {
    return column.type === 'error-count' && Number(row[column.key]) > 0;
  }

  isWarningCount(
    column: WorkspaceSimpleTableColumn<T>,
    row: T,
  ): boolean {
    return column.type === 'warning-count' && Number(row[column.key]) > 0;
  }

  isStatus(column: WorkspaceSimpleTableColumn<T>): boolean {
    return column.type === 'status';
  }

  statusClass(value: unknown): string {
    if (value === 'valid') {
      return 'status-valid';
    }

    if (value === 'warning') {
      return 'status-warning';
    }

    if (value === 'error') {
      return 'status-error';
    }

    return '';
  }

  displayValue(value: unknown): string {
    return String(value ?? '');
  }

  statusLabel(value: unknown): string {
    if (value === 'valid') {
      return 'Valid';
    }

    if (value === 'warning') {
      return 'Warning';
    }

    if (value === 'error') {
      return 'Error';
    }

    return String(value ?? '');
  }
}
