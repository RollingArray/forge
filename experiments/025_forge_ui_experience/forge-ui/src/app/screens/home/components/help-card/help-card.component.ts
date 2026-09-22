import {
  ChangeDetectionStrategy,
  Component,
  output,
} from '@angular/core';

@Component({
  selector: 'app-help-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './help-card.component.html',
  styleUrl: './help-card.component.css',
})
export class HelpCardComponent {
  readonly actionSelected = output<string>();

  openDocumentation(): void {
    this.actionSelected.emit('documentation');
  }
}
