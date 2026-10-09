import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import {
  GenerationArtifact,
  GenerationArtifactPreview,
} from '../../results.models';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSimpleTableComponent } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkspaceSimpleTableColumn } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.models';

@Component({
  selector: 'app-artifact-preview',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceSimpleTableComponent,
  ],
  templateUrl: './artifact-preview.component.html',
  styleUrl: './artifact-preview.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactPreviewComponent {
  readonly artifact = input<GenerationArtifact | null>(null);
  readonly preview = input<GenerationArtifactPreview | null>(null);
  readonly loading = input(false);
  readonly error = input<string | null>(null);

  readonly downloadRequested = output<GenerationArtifact>();

  readonly searchTerm = signal('');

  readonly tableColumns = computed<
    readonly WorkspaceSimpleTableColumn<Record<string, unknown>>[]
  >(() =>
    (this.preview()?.columns ?? []).map((column) => ({
      key: column,
      label: column,
      width: 'minmax(120px, max-content)',
    })),
  );

  readonly filteredRows = computed(() => {
    const preview = this.preview();
    const searchTerm = this.searchTerm().trim().toLowerCase();

    if (!preview || !searchTerm) {
      return preview?.rows ?? [];
    }

    return preview.rows.filter((row) =>
      preview.columns.some((column) =>
        String(row[column] ?? '')
          .toLowerCase()
          .includes(searchTerm),
      ),
    );
  });

  updateSearchTerm(value: string): void {
    this.searchTerm.set(value);
  }

  download(): void {
    const artifact = this.artifact();

    if (artifact) {
      this.downloadRequested.emit(artifact);
    }
  }
}
