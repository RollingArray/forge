import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  TemplateRef,
  viewChild,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { GenerationArtifact } from '../../results.models';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSimpleTableComponent } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.component';
import {
  WorkspaceSimpleTableCellContext,
  WorkspaceSimpleTableColumn,
} from '../../../../shared/components/workspace-simple-table/workspace-simple-table.models';

@Component({
  selector: 'app-generated-files',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceSimpleTableComponent,
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

  readonly filenameTemplate =
    viewChild<TemplateRef<WorkspaceSimpleTableCellContext<GenerationArtifact>>>(
      'filenameTemplate',
    );
  readonly sizeTemplate =
    viewChild<TemplateRef<WorkspaceSimpleTableCellContext<GenerationArtifact>>>(
      'sizeTemplate',
    );
  readonly downloadTemplate =
    viewChild<TemplateRef<WorkspaceSimpleTableCellContext<GenerationArtifact>>>(
      'downloadTemplate',
    );

  readonly columns = computed<
    readonly WorkspaceSimpleTableColumn<GenerationArtifact>[]
  >(() => {
    const filenameTemplate = this.filenameTemplate();
    const sizeTemplate = this.sizeTemplate();
    const downloadTemplate = this.downloadTemplate();

    return [
      { key: 'entity_name', label: '#', type: 'index', width: '36px', align: 'center' },
      { key: 'filename', label: 'File Name', width: 'minmax(180px, 1fr)', template: filenameTemplate },
      { key: 'rows', label: 'Rows', type: 'number', width: '80px', align: 'right' },
      { key: 'size_bytes', label: 'Size', width: '90px', align: 'right', template: sizeTemplate },
      { key: 'entity_name', label: 'Actions', width: '64px', align: 'center', template: downloadTemplate },
    ];
  });

  readonly searchTermChange = output<string>();
  readonly artifactSelected = output<GenerationArtifact>();
  readonly downloadRequested = output<GenerationArtifact>();

  updateSearchTerm(value: string): void {
    this.searchTermChange.emit(value);
  }

  selectTableRow(artifact: GenerationArtifact): void {
    this.selectArtifact(artifact);
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
