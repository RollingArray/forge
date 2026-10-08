import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

export type WorkflowRowColumns = 1 | 2 | 3 | 4;

@Component({
  selector: 'app-workflow-row',
  standalone: true,
  templateUrl: './workflow-row.component.html',
  styleUrl: './workflow-row.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkflowRowComponent {
  readonly columns = input<WorkflowRowColumns>(1);
}
