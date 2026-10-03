import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

@Component({
  selector: 'app-workspace-table-empty',
  standalone: true,
  templateUrl: './workspace-table-empty.component.html',
  styleUrl: './workspace-table-empty.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceTableEmptyComponent {
  readonly message = input('No results found.');
}
