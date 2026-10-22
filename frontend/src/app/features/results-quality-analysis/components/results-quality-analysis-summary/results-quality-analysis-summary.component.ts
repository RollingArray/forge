import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';

@Component({
  selector: 'app-results-quality-analysis-summary',
  standalone: true,
  imports: [
    MetricGridComponent,
    WorkspaceHeaderComponent,
    WorkspaceSectionComponent,
  ],
  templateUrl: './results-quality-analysis-summary.component.html',
  styleUrl: './results-quality-analysis-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsQualityAnalysisSummaryComponent {
  readonly metrics = input.required<MetricCardData[]>();
  readonly jobId = input.required<string>();
  readonly modelName = input.required<string>();
  readonly modelDescription = input.required<string>();
}
