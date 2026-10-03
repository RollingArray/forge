import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';

@Component({
  selector: 'app-workspace-table',
  standalone: true,
  templateUrl: './workspace-table.component.html',
  styleUrl: './workspace-table.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceTableComponent {}
