import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { DecimalPipe } from '@angular/common';

@Component({
  selector: 'app-generation-target-card',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './generation-target-card.component.html',
  styleUrl: './generation-target-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationTargetCardComponent {
  readonly totalTargetRows = input(0);
}
