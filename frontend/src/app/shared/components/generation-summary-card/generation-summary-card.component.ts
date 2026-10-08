import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

@Component({
  selector: 'app-generation-summary-card',
  standalone: true,
  templateUrl: './generation-summary-card.component.html',
  styleUrl: './generation-summary-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationSummaryCardComponent {
  readonly label = input.required<string>();
  readonly value = input.required<string>();
  readonly detail = input.required<string>();
}
