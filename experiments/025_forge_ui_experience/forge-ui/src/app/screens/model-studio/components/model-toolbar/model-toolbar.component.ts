import {
  ChangeDetectionStrategy,
  Component,
  output,
  signal,
} from '@angular/core';

@Component({
  selector: 'app-model-toolbar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './model-toolbar.component.html',
  styleUrl: './model-toolbar.component.css',
})
export class ModelToolbarComponent {
  readonly actionSelected = output<string>();

  readonly showFields = signal(true);
  readonly showKeys = signal(true);
  readonly showRelationships = signal(true);

  selectAction(action: string): void {
    this.actionSelected.emit(action);
  }

  toggleFields(): void {
    this.showFields.update(value => !value);
    this.actionSelected.emit('toggle-fields');
  }

  toggleKeys(): void {
    this.showKeys.update(value => !value);
    this.actionSelected.emit('toggle-keys');
  }

  toggleRelationships(): void {
    this.showRelationships.update(value => !value);
    this.actionSelected.emit('toggle-relationships');
  }
}
