import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

@Component({
  selector: 'app-workflow-page-header',
  standalone: true,
  templateUrl: './workflow-page-header.component.html',
  styleUrl: './workflow-page-header.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkflowPageHeaderComponent {
  readonly icon = input.required<string>();
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  readonly progress = input.required<string>();
}
