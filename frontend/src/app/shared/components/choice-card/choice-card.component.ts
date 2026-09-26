import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

@Component({
  selector: 'app-choice-card',
  standalone: true,
  templateUrl: './choice-card.component.html',
  styleUrl: './choice-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChoiceCardComponent {
  readonly icon = input.required<string>();
  readonly title = input.required<string>();
  readonly description = input.required<string>();
  readonly example = input<string>('');
  readonly selected = input(false);

  readonly selectedChange = output<void>();

  select(): void {
    this.selectedChange.emit();
  }
}
