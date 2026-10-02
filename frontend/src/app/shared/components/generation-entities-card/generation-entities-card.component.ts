import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-generation-entities-card',
  standalone: true,
  templateUrl: './generation-entities-card.component.html',
  styleUrl: './generation-entities-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationEntitiesCardComponent {
  readonly entityCount = input<number | null>(null);
}
