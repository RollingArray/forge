import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { WorkflowRowComponent } from '../../../../shared/components/workflow-row/workflow-row.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSimpleTableComponent } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkspaceSimpleTableColumn } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.models';

interface AssumptionTableRow {
  id: number;
  assumption: string;
}

@Component({
  selector: 'app-assumptions-review',
  standalone: true,
  imports: [
    WorkflowRowComponent,
    WorkspaceHeaderComponent,
    WorkspaceSimpleTableComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './assumptions-review.component.html',
})
export class AssumptionsReviewComponent {
  readonly assumptions = input<string[]>([]);

  readonly columns: readonly WorkspaceSimpleTableColumn<AssumptionTableRow>[] = [
    {
      key: 'assumption',
      label: 'Assumption',
      width: 'minmax(0, 1fr)',
    },
  ];

  readonly tableRows = computed(() =>
    this.assumptions().map((assumption, index) => ({
      id: index + 1,
      assumption,
    })),
  );

  readonly tableHeight = computed(() =>
    `${Math.min(42 + this.tableRows().length * 54, 420)}px`,
  );
}
