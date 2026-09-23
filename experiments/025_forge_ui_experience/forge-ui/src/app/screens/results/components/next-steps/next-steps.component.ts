import {
  ChangeDetectionStrategy,
  Component,
  output,
} from '@angular/core';

@Component({
  selector: 'app-results-next-steps',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './next-steps.component.html',
  styleUrl: './next-steps.component.css',
})
export class NextStepsComponent {
  readonly newGeneration =
    output<void>();

  readonly modelStudio =
    output<void>();
}
