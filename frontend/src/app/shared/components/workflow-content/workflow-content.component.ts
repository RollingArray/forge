import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';

@Component({
  selector: 'app-workflow-content',
  standalone: true,
  templateUrl: './workflow-content.component.html',
  styleUrl: './workflow-content.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkflowContentComponent {}
