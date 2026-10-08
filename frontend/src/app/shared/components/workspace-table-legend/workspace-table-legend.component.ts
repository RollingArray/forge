import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

export type WorkspaceTableLegendVariant =
  | 'neutral'
  | 'primary'
  | 'success'
  | 'warning'
  | 'error';

export interface WorkspaceTableLegendItem {
  label: string;
  description: string;
  icon?: string;
  variant?: WorkspaceTableLegendVariant;
}

@Component({
  selector: 'app-workspace-table-legend',
  standalone: true,
  templateUrl: './workspace-table-legend.component.html',
  styleUrl: './workspace-table-legend.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceTableLegendComponent {
  readonly items = input.required<readonly WorkspaceTableLegendItem[]>();
}
