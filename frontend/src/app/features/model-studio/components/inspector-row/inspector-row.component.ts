import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-inspector-row',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './inspector-row.component.html',
  styleUrl: './inspector-row.component.css',
})
export class InspectorRowComponent {
  readonly icon = input.required<string>();
  readonly ariaLabel = input.required<string>();
  readonly showEdit = input(false);
  readonly variant = input<'default' | 'compact'>('default');
  readonly edit = output<void>();
}
