import { NgTemplateOutlet } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { WorkspaceTableEmptyComponent } from '../workspace-table-empty/workspace-table-empty.component';
import { WorkspaceTableToolbarComponent } from '../workspace-table-toolbar/workspace-table-toolbar.component';
import {
  WorkspaceSimpleTableCellContext,
  WorkspaceSimpleTableColumn,
  WorkspaceSimpleTableHeaderContext,
} from './workspace-simple-table.models';

@Component({
  selector: 'app-workspace-simple-table',
  standalone: true,
  imports: [
    WorkspaceTableToolbarComponent,
    WorkspaceTableEmptyComponent,
    NgTemplateOutlet,
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

  readonly height = input('360px');

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

  getCellContext(
    row: T,
    column: WorkspaceSimpleTableColumn<T>,
    index: number,
  ): WorkspaceSimpleTableCellContext<T> {
    return {
      $implicit: row,
      row,
      column,
      value: this.getCellValue(row, column),
      index,
    };
  }

  getGridTemplateColumns(): string {
    return this.columns()
      .map((column) => column.width ?? 'minmax(0, 1fr)')
      .join(' ');
  }

  getColumnAlignClass(
    column: WorkspaceSimpleTableColumn<T>,
  ): string {
    return `align-${column.align ?? 'left'}`;
  }

  getHeaderContext(
    column: WorkspaceSimpleTableColumn<T>,
  ): WorkspaceSimpleTableHeaderContext<T> {
    return {
      $implicit: column,
      column,
    };
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

  isIndex(column: WorkspaceSimpleTableColumn<T>): boolean {
    return column.type === 'index';
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
