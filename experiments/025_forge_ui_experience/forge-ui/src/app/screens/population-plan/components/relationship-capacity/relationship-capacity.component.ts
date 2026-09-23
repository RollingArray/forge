import { DecimalPipe } from '@angular/common';

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {
  PopulationCapacityLimit,
  PopulationCapacityRequirement,
  PopulationRelationshipRequirement,
} from '../../models/population-plan.models';

@Component({
  selector: 'app-relationship-capacity',
  standalone: true,
  imports: [DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './relationship-capacity.component.html',
  styleUrl: './relationship-capacity.component.css',
})
export class RelationshipCapacityComponent {
  readonly relationshipRequirements =
    input<readonly PopulationRelationshipRequirement[]>([]);

  readonly capacityRequirements =
    input<readonly PopulationCapacityRequirement[]>([]);

  readonly capacityLimits =
    input<readonly PopulationCapacityLimit[]>([]);

  readonly issueCount = computed(
    () =>
      this.capacityRequirements().length +
      this.capacityLimits().length,
  );

  readonly relationshipCount = computed(
    () => this.relationshipRequirements().length,
  );
}
