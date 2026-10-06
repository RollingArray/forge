import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

export type StatusCardState =
  | 'success'
  | 'warning'
  | 'error'
  | 'info'
  | 'neutral';

@Component({
  selector: 'app-status-card',
  standalone: true,
  templateUrl: './status-card.component.html',
  styleUrl: './status-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatusCardComponent {
  readonly label = input.required<string>();
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  readonly status = input.required<StatusCardState>();
}
