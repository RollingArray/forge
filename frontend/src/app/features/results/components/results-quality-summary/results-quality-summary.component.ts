import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { GenerationQualityProfile } from '../../results.models';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';

@Component({
  selector: 'app-results-quality-summary',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
  ],
  templateUrl: './results-quality-summary.component.html',
  styleUrl: './results-quality-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsQualitySummaryComponent {
  readonly quality = input<GenerationQualityProfile | null>(null);
  readonly viewDetails = output<void>();

  populationFidelity(): number {
    return Number(
      (this.quality()?.population_fidelity as Record<string, unknown>)
        ?.['fidelity_rate'] ?? 0,
    ) * 100;
  }

  distributionCount(): number {
    return Number(
      (this.quality()?.distribution_fidelity as Record<string, unknown>)
        ?.['fields_analyzed'] ?? 0,
    );
  }

  relationshipCount(): number {
    return Number(
      (this.quality()?.relationship_fidelity as Record<string, unknown>)
        ?.['relationships_analyzed'] ?? 0,
    );
  }

  statisticalCount(): number {
    return Number(
      (this.quality()?.statistical_fidelity as Record<string, unknown>)
        ?.['numeric_fields_analyzed'] ?? 0,
    );
  }

  performance(): number {
    return Number(
      (this.quality()?.performance as Record<string, unknown>)
        ?.['rows_per_second'] ?? 0,
    );
  }

  identityCount(): number {
    const identity = this.quality()?.identity_space_utilization as
      | Record<string, unknown>
      | undefined;

    return Number(identity?.['entities_analyzed'] ?? 0);
  }
}
