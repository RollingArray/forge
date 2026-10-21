import { CommonModule } from '@angular/common';
import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { ValidationCheck } from '../../../../core/interfaces/validation-check.interface';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { ValidationCheckCardComponent } from '../validation-check-card/validation-check-card.component';

@Component({
  selector: 'app-validation-evidence',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceScrollAreaComponent,
    ValidationCheckCardComponent,
  ],
  templateUrl: './validation-evidence.component.html',
  styleUrl: './validation-evidence.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ValidationEvidenceComponent {
  readonly checks = input.required<readonly ValidationCheck[]>();
}
