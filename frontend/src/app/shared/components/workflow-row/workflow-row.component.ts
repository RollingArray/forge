import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

export type WorkflowRowColumns = 1 | 2 | 3 | 4 | `${number}-${number}`;

@Component({
  selector: 'app-workflow-row',
  standalone: true,
  templateUrl: './workflow-row.component.html',
  styleUrl: './workflow-row.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkflowRowComponent {
  readonly columns = input<WorkflowRowColumns>(1);

  customColumns(): string | null {
    const value = this.columns();

    if (typeof value !== 'string') {
      return null;
    }

    const ratios = value.split('-').map(Number);

    if (
      ratios.length !== 2 ||
      ratios.some((ratio) => !Number.isFinite(ratio) || ratio <= 0)
    ) {
      return null;
    }

    return ratios.map((ratio) => `minmax(0, ${ratio}fr)`).join(' ');
  }
}
