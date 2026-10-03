import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

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

  readonly showSearch = input(false);
  readonly searchPlaceholder = input('Search...');
  readonly searchValue = input('');

  readonly showDownload = input(false);

  readonly searchValueChange = output<string>();
  readonly download = output<void>();

  onSearch(value: string): void {
    this.searchValueChange.emit(value);
  }

  onDownload(): void {
    this.download.emit();
  }
}
