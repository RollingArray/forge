import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { GenerationValidationSummary } from '../../results.models';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';

@Component({
  selector: 'app-results-validation',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
  ],
  templateUrl: './results-validation.component.html',
  styleUrl: './results-validation.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsValidationComponent {
  readonly validation = input<GenerationValidationSummary | null>(null);

  foreignKeyCount(): number {
    const evidence = this.validation()?.evidence as Record<string, any> | undefined;
    return evidence?.['foreign_keys']?.['relationships_checked'] ?? 0;
  }

  constraintCount(): number {
    const evidence = this.validation()?.evidence as Record<string, any> | undefined;
    return evidence?.['constraints']?.['constraints_checked'] ?? 0;
  }
}
