import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import type { ValidationFinding } from '../../../../core/interfaces/validation-finding.interface';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import {
  WorkspaceTableToolbarComponent,
  WorkspaceToolbarFilter,
} from '../../../../shared/components/workspace-table-toolbar/workspace-table-toolbar.component';

@Component({
  selector: 'app-validation-findings',
  standalone: true,
  imports: [
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceScrollAreaComponent,
    WorkspaceTableToolbarComponent,
  ],
  templateUrl: './validation-findings.component.html',
  styleUrl: './validation-findings.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ValidationFindingsComponent {
  readonly findings = input.required<readonly ValidationFinding[]>();
  readonly filters = input.required<WorkspaceToolbarFilter[]>();
  readonly searchValue = input('');

  readonly searchValueChange = output<string>();
  readonly filterChange = output<string>();
}
