import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { GenerationExecutionSummaryResponse } from '../../../generate/models/generation.models';
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
  readonly execution = input<GenerationExecutionSummaryResponse | null>(null);
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

  statusLabel(): string {
    const status = this.execution()?.status;

    switch (status) {
      case 'COMPLETED':
        return 'Generation completed';
      case 'PARTIALLY_COMPLETED':
        return 'Generation partially completed';
      case 'FAILED':
        return 'Generation failed';
      case 'CANCELLED':
        return 'Generation cancelled';
      case 'RUNNING':
        return 'Generation running';
      case 'QUEUED':
        return 'Generation queued';
      case 'PLANNING':
        return 'Generation planning';
      case 'INTERRUPTED':
        return 'Generation interrupted';
      case 'CREATED':
        return 'Generation created';
      default:
        return 'Generation status unavailable';
    }
  }

  totalTime(): number | null {
    return this.execution()?.elapsed_seconds ?? null;
  }

  throughput(): number | null {
    return this.execution()?.throughput_rows_per_second ?? null;
  }

  peakMemory(): number | null {
    return this.execution()?.peak_memory_mb ?? null;
  }

  entityCount(): number {
    return this.execution()?.entity_count ?? 0;
  }

  completedEntityCount(): number {
    return this.execution()?.completed_entity_count ?? 0;
  }

  failedEntityCount(): number {
    return this.execution()?.failed_entity_count ?? 0;
  }

  progress(): number {
    const job = this.execution();

    if (!job?.total_target_rows) {
      return 0;
    }

    return Math.min(
      100,
      (job.total_generated_rows / job.total_target_rows) * 100,
    );
  }
}
