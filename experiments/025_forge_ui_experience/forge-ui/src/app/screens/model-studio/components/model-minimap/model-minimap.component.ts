import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { CanvasEntity } from '../../models/model-studio.models';

interface CanvasViewport {
  left: number;
  top: number;
  width: number;
  height: number;
}

@Component({
  selector: 'app-model-minimap',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './model-minimap.component.html',
  styleUrl: './model-minimap.component.css',
})
export class ModelMinimapComponent {
  readonly entities = input.required<CanvasEntity[]>();

  readonly viewport = input<CanvasViewport>({
    left: 0,
    top: 0,
    width: 0,
    height: 0,
  });

  readonly canvasWidth = 2100;
  readonly canvasHeight = 1250;
  readonly minimapScale = 0.075;

  get viewportLeft(): number {
    return this.viewport().left * this.minimapScale;
  }

  get viewportTop(): number {
    return this.viewport().top * this.minimapScale;
  }

  get viewportWidth(): number {
    return Math.min(
      this.viewport().width * this.minimapScale,
      this.canvasWidth * this.minimapScale,
    );
  }

  get viewportHeight(): number {
    return Math.min(
      this.viewport().height * this.minimapScale,
      this.canvasHeight * this.minimapScale,
    );
  }
}
