import {
  ChangeDetectionStrategy,
  Component,
  output,
} from '@angular/core';

@Component({
  selector: 'app-dataset-actions',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './dataset-actions.component.html',
  styleUrl: './dataset-actions.component.css',
})
export class DatasetActionsComponent {
  readonly explore =
    output<void>();

  readonly manifest =
    output<void>();
}
