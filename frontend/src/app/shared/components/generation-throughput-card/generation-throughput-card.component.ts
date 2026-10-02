import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { DecimalPipe } from '@angular/common';

@Component({
  selector: 'app-generation-throughput-card',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './generation-throughput-card.component.html',
  styleUrl: './generation-throughput-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationThroughputCardComponent {
  readonly throughputRowsPerSecond = input<number | null>(null);
}
