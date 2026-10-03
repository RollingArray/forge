import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { GenerationJobResponse } from '../../../generate/models/generation.models';

@Component({
  selector: 'app-results-execution-summary',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './results-execution-summary.component.html',
  styleUrl: './results-execution-summary.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultsExecutionSummaryComponent {
  readonly generationJob = input<GenerationJobResponse | null>(null);
  readonly jobId = input('');
  readonly dataModelName = input('');

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
