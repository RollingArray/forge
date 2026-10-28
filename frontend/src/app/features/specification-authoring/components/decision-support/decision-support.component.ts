import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { AIWholeSpecificationDecisionItem } from '../../../../core/interfaces/ai-whole-specification-proposal.interface';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { ForgeButtonComponent } from '../../../../shared/components/forge-button/forge-button.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkflowRowComponent } from '../../../../shared/components/workflow-row/workflow-row.component';

@Component({
  selector: 'app-decision-support',
  standalone: true,
  imports: [WorkspaceSectionComponent, WorkspaceHeaderComponent, ForgeButtonComponent, WorkflowRowComponent],
  templateUrl: './decision-support.component.html',
  styleUrl: './decision-support.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DecisionSupportComponent {
  readonly items = input<AIWholeSpecificationDecisionItem[]>([]);
  readonly answers = input<Record<string, string>>({});
  readonly requestInProgress = input(false);
  readonly requiredDecisionsComplete = input(false);

  readonly answerChange = output<{ id: string; value: string }>();
  readonly useRecommendation = output<{ id: string; proposedValue: string }>();
  readonly updateMainDescription = output<void>();
}
