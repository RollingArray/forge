import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { WorkflowRowComponent, WorkflowRowColumns } from '../workflow-row/workflow-row.component';

@Component({
  selector: 'app-content-grid',
  standalone: true,
  imports: [WorkflowRowComponent],
  templateUrl: './content-grid.component.html',
  styleUrl: './content-grid.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContentGridComponent {
  readonly columns = input<WorkflowRowColumns>(1);
}
