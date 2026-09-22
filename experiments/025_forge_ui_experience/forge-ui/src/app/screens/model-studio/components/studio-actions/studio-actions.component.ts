import {
  ChangeDetectionStrategy,
  Component,
  output,
} from '@angular/core';

@Component({
  selector: 'app-studio-actions',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './studio-actions.component.html',
  styleUrl: './studio-actions.component.css',
})
export class StudioActionsComponent {
  readonly actionSelected = output<string>();

  select(action: string): void {
    this.actionSelected.emit(action);
  }
}
