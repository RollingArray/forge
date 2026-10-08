import { TemplateRef } from '@angular/core';

export type WorkspaceSimpleTableColumnType =
  | 'text'
  | 'number'
  | 'error-count'
  | 'warning-count'
  | 'status'
  | 'index';

export type WorkspaceSimpleTableColumnAlign =
  | 'left'
  | 'center'
  | 'right';

export interface WorkspaceSimpleTableCellContext<T extends object> {
  $implicit: T;
  row: T;
  column: WorkspaceSimpleTableColumn<T>;
  value: unknown;
  index: number;
}

export interface WorkspaceSimpleTableHeaderContext<T extends object> {
  $implicit: WorkspaceSimpleTableColumn<T>;
  column: WorkspaceSimpleTableColumn<T>;
}

export interface WorkspaceSimpleTableColumn<T extends object> {
  key: keyof T;
  label: string;
  type?: WorkspaceSimpleTableColumnType;
  width?: string;
  align?: WorkspaceSimpleTableColumnAlign;
  template?: TemplateRef<WorkspaceSimpleTableCellContext<T>>;
  headerTemplate?: TemplateRef<WorkspaceSimpleTableHeaderContext<T>>;
}
