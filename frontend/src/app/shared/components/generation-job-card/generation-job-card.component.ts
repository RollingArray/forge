import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-generation-job-card',
  standalone: true,
  templateUrl: './generation-job-card.component.html',
  styleUrl: './generation-job-card.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationJobCardComponent {
  readonly jobId = input<string | null>(null);
  readonly exists = input(false);
}
