/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: data-model-card.component.ts
 * Purpose: Defines the data model card Workspace component.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { DataModel } from '../../../../core/interfaces/data-model.interface';

@Component({
  selector: 'app-data-model-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './data-model-card.component.html',
  styleUrl: './data-model-card.component.css',
})
export class DataModelCardComponent {
  readonly dataModel = input.required<DataModel>();
  readonly selected = input(false);

  readonly selectedChange = output<DataModel>();

  select(): void {
    this.selectedChange.emit(this.dataModel());
  }
}
