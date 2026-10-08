import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { DecimalPipe } from '@angular/common';

import { PopulationCandidatePlan } from '../../models/population.models';

@Component({
  selector: 'app-population-candidate-decision',
  standalone: true,
  imports: [DecimalPipe],
  templateUrl: './population-candidate-decision.component.html',
  styleUrl: './population-candidate-decision.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PopulationCandidateDecisionComponent {
  readonly candidate = input.required<PopulationCandidatePlan>();
  readonly entityCount = input.required<number>();
}
