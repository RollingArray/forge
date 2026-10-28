import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';

@Component({
  selector: 'app-assumptions-review',
  standalone: true,
  imports: [WorkspaceSectionComponent, WorkspaceHeaderComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assumptions-review.component.html',
})
export class AssumptionsReviewComponent {
  readonly assumptions = input<string[]>([]);
}
