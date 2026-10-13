import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-empty-inspector-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './empty-inspector-state.component.html',
  styleUrl: './empty-inspector-state.component.css',
})
export class EmptyInspectorStateComponent {
  readonly icon = input.required<string>();
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  readonly actionLabel = input.required<string>();
  readonly action = output<void>();
}
