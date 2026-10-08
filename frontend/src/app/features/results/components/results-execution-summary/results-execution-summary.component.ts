import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { GenerationJobResponse } from '../../../generate/models/generation.models';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';

@Component({
  selector: 'app-results-execution-summary',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceHeaderComponent,
    WorkspaceSectionComponent,
    MetricGridComponent,
  ],
  templateUrl: './results-execution-summary.component.html',
  styleUrl: './results-execution-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsExecutionSummaryComponent {
  readonly generationJob = input<GenerationJobResponse | null>(null);
  readonly jobId = input('');
  readonly dataModelName = input('');

  readonly metrics = (): MetricCardData[] => [
    {
      label: 'Total Time',
      value: this.totalTime() !== null
        ? `${this.totalTime()!.toFixed(2)} s`
        : '—',
      description: 'Total generation time',
      icon: 'schedule',
    },
    {
      label: 'Throughput',
      value: this.throughput() !== null
        ? `${Math.round(this.throughput()!)}`
        : '—',
      description: 'Rows generated per second',
      icon: 'bar_chart',
    },
    {
      label: 'Peak Memory',
      value: this.peakMemory() !== null
        ? `${this.peakMemory()!.toFixed(1)} MB`
        : '—',
      description: 'Peak process memory',
      icon: 'database',
    },
    {
      label: 'Entities',
      value: this.entityCount(),
      description: `${this.completedEntityCount()} completed · ${this.failedEntityCount()} failed`,
      icon: 'format_list_numbered',
    },
  ];

  totalTime(): number | null {
    return this.generationJob()?.elapsed_seconds ?? null;
  }

  throughput(): number | null {
    return this.generationJob()?.throughput_rows_per_second ?? null;
  }

  peakMemory(): number | null {
    return this.generationJob()?.peak_memory_mb ?? null;
  }

  entityCount(): number {
    return this.generationJob()?.entities?.length ?? 0;
  }

  completedEntityCount(): number {
    return (
      this.generationJob()?.entities?.filter(
        (entity) => entity.status === 'COMPLETED',
      ).length ?? 0
    );
  }

  failedEntityCount(): number {
    return (
      this.generationJob()?.entities?.filter(
        (entity) => entity.status === 'FAILED',
      ).length ?? 0
    );
  }

  progress(): number {
    const job = this.generationJob();

    if (!job?.total_target_rows) {
      return 0;
    }

    return Math.min(
      100,
      (job.total_generated_rows / job.total_target_rows) * 100,
    );
  }
}
