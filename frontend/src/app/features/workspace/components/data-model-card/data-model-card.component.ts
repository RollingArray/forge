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
  signal,
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
  readonly editRequested = output<DataModel>();
  readonly shareRequested = output<DataModel>();
  readonly duplicateRequested = output<DataModel>();
  readonly actionsMenuOpen = signal(false);

  select(): void {
    if (this.actionsMenuOpen()) return;
    this.selectedChange.emit(this.dataModel());
  }

  toggleActionsMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.actionsMenuOpen.update((open) => !open);
  }

  closeActionsMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.actionsMenuOpen.set(false);
  }

  duplicate(event: MouseEvent): void {
    event.stopPropagation();
    this.actionsMenuOpen.set(false);
    this.duplicateRequested.emit(this.dataModel());
  }

  edit(event: MouseEvent): void {
    event.stopPropagation();
    this.actionsMenuOpen.set(false);
    this.editRequested.emit(this.dataModel());
  }

  share(event: MouseEvent): void {
    event.stopPropagation();
    this.shareRequested.emit(this.dataModel());
  }
}
