/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: recent-data-models.component.ts
 * Purpose: Defines the recent data models Workspace component.
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
import { DataModelCardComponent } from '../data-model-card/data-model-card.component';

@Component({
  selector: 'app-workspace-recent-data-models',
  standalone: true,
  imports: [DataModelCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './recent-data-models.component.html',
  styleUrl: './recent-data-models.component.css',
})
export class RecentDataModelsComponent {
  readonly dataModels = input.required<DataModel[]>();
  readonly selectedDataModel = input<DataModel | null>(null);

  readonly dataModelSelected = output<DataModel>();
  readonly newDataModel = output<void>();

  selectDataModel(dataModel: DataModel): void {
    this.dataModelSelected.emit(dataModel);
  }

  createDataModel(): void {
    this.newDataModel.emit();
  }

}
