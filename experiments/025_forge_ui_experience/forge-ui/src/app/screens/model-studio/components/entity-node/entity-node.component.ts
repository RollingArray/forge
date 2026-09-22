import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { CanvasEntity } from '../../models/model-studio.models';

@Component({
  selector: 'app-entity-node',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-node.component.html',
  styleUrl: './entity-node.component.css',
})
export class EntityNodeComponent {
  readonly entity =
    input.required<CanvasEntity>();

  readonly selected =
    input(false);

  readonly selectedChange =
    output<string>();

  select(): void {
    this.selectedChange.emit(
      this.entity().name,
    );
  }
}
