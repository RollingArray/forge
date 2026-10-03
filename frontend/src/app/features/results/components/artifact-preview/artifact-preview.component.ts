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
import { WorkspaceTableComponent } from '../../../../shared/components/workspace-table/workspace-table.component';
import { WorkspaceTableToolbarComponent } from '../../../../shared/components/workspace-table-toolbar/workspace-table-toolbar.component';
import { WorkspaceTableEmptyComponent } from '../../../../shared/components/workspace-table-empty/workspace-table-empty.component';

@Component({
  selector: 'app-artifact-preview',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceTableComponent,
    WorkspaceTableToolbarComponent,
    WorkspaceTableEmptyComponent,
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
