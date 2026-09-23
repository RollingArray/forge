import {
  ChangeDetectionStrategy,
  Component,
  output,
  input,
} from '@angular/core';

import { DecimalPipe } from '@angular/common';

import {
  PopulationTableRow,
} from '../../models/population-plan.models';

export interface PopulationRequestedChange {
  readonly entity: string;
  readonly requested: number;
}

@Component({
  selector: 'app-entity-population-table',
  standalone: true,
  imports: [DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-population-table.component.html',
  styleUrl: './entity-population-table.component.css',
})
export class EntityPopulationTableComponent {
  readonly rows =
    input<readonly PopulationTableRow[]>([]);

  readonly requestedChange =
    output<PopulationRequestedChange>();

  updateRequested(
    entity: string,
    value: string,
  ): void {
    const requested = Number(value);

    if (!Number.isFinite(requested) || requested < 0) {
      return;
    }

    this.requestedChange.emit({
      entity,
      requested: Math.floor(requested),
    });
  }
}
