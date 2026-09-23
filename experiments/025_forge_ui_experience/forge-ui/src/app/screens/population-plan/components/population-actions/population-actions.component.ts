import {
  ChangeDetectionStrategy,
  Component,
  output,
} from '@angular/core';

@Component({
  selector: 'app-population-actions',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './population-actions.component.html',
  styleUrl: './population-actions.component.css',
})
export class PopulationActionsComponent {
  readonly actionSelected = output<string>();

  select(action: string): void {
    this.actionSelected.emit(action);
  }
}
