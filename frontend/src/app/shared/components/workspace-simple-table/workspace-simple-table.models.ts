export type WorkspaceSimpleTableColumnType =
  | 'text'
  | 'number'
  | 'error-count'
  | 'warning-count'
  | 'status';

export interface WorkspaceSimpleTableColumn<T> {
  key: keyof T;
  label: string;
  type?: WorkspaceSimpleTableColumnType;
}
