/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: color-picker.component.ts
 * Purpose: Reusable FORGE color selection component.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  effect,
  input,
  output,
  signal,
} from '@angular/core';

import { DataModelColor } from '../../../core/enums/data-model-color.enum';

@Component({
  selector: 'app-color-picker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './color-picker.component.html',
  styleUrl: './color-picker.component.css',
})
export class ColorPickerComponent {
  readonly selectedColor = input<DataModelColor | null>(null);

  readonly colorSelected = output<DataModelColor>();

  readonly colors = Object.values(DataModelColor);

  readonly activeColor = signal<DataModelColor>(
    this.getRandomColor(),
  );

  constructor() {
    effect(() => {
      const selectedColor = this.selectedColor();

      if (selectedColor) {
        this.activeColor.set(selectedColor);
      }
    });
  }

  selectColor(color: DataModelColor): void {
    this.activeColor.set(color);
    this.colorSelected.emit(color);
  }

  private getRandomColor(): DataModelColor {
    const index = Math.floor(Math.random() * this.colors.length);

    return this.colors[index];
  }
}
