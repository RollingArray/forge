import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-inspector-shell',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './inspector-shell.component.html',
  styleUrl: './inspector-shell.component.css',
})
export class InspectorShellComponent {
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  readonly actionLabel = input<string>();
  readonly actionIcon = input<string>();
  readonly actionVariant = input<'primary' | 'secondary'>('primary');
  readonly action = output<void>();
}
