import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { EntityGenerationRow } from '../../models/generate.models';

@Component({
  selector: 'app-current-activity',
  standalone: true,
  templateUrl: './current-activity.component.html',
  styleUrl: './current-activity.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CurrentActivityComponent {
  readonly completed =
    input.required<boolean>();

  readonly entity =
    input<EntityGenerationRow | null>(null);

  readonly updatedAt =
    input.required<string>();

  formatDate(value: string): string {
    return new Date(value).toLocaleString();
  }
}
