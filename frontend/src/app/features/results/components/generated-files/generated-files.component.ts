import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { GenerationArtifact } from '../../results.models';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceTableComponent } from '../../../../shared/components/workspace-table/workspace-table.component';
import { WorkspaceTableToolbarComponent } from '../../../../shared/components/workspace-table-toolbar/workspace-table-toolbar.component';
import { WorkspaceTableEmptyComponent } from '../../../../shared/components/workspace-table-empty/workspace-table-empty.component';

@Component({
  selector: 'app-generated-files',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceTableComponent,
    WorkspaceTableToolbarComponent,
    WorkspaceTableEmptyComponent,
  ],
  templateUrl: './generated-files.component.html',
  styleUrl: './generated-files.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GeneratedFilesComponent {
  readonly artifacts = input.required<GenerationArtifact[]>();
  readonly allArtifactsCount = input(0);
  readonly loading = input(false);
  readonly error = input<string | null>(null);
  readonly selectedArtifact = input<GenerationArtifact | null>(null);
  readonly searchTerm = input('');

  readonly searchTermChange = output<string>();
  readonly artifactSelected = output<GenerationArtifact>();
  readonly downloadRequested = output<GenerationArtifact>();

  updateSearchTerm(value: string): void {
    this.searchTermChange.emit(value);
  }

  selectArtifact(artifact: GenerationArtifact): void {
    this.artifactSelected.emit(artifact);
  }

  downloadArtifact(
    event: MouseEvent,
    artifact: GenerationArtifact,
  ): void {
    event.stopPropagation();
    this.downloadRequested.emit(artifact);
  }

  isSelected(artifact: GenerationArtifact): boolean {
    return (
      this.selectedArtifact()?.entity_name === artifact.entity_name
    );
  }
}
