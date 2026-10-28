import { Component, ChangeDetectionStrategy, computed, input } from '@angular/core';
import { ValidationCheck } from '../../../../core/interfaces/validation-check.interface';
import { ContentCardComponent } from '../../../../shared/components/content-card/content-card.component';
import { ContentGridComponent } from '../../../../shared/components/content-grid/content-grid.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { ValidationCheckCardComponent } from '../validation-check-card/validation-check-card.component';

@Component({
  selector: 'app-validation-evidence',
  standalone: true,
  imports: [
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceScrollAreaComponent,
    ContentGridComponent,
    ContentCardComponent,
    ValidationCheckCardComponent,
  ],
  templateUrl: './validation-evidence.component.html',
  styleUrl: './validation-evidence.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ValidationEvidenceComponent {
  readonly checks = input.required<readonly ValidationCheck[]>();

  readonly visibleChecks = computed(() =>
    this.checks().filter((check) => check.key !== 'coverage'),
  );
}
