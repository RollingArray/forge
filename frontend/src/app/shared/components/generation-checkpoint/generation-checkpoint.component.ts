import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { GenerationCheckpoint } from '../../models/generation-checkpoint.models';

@Component({
  selector: 'app-generation-checkpoint',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './generation-checkpoint.component.html',
  styleUrl: './generation-checkpoint.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationCheckpointComponent {
  readonly checkpoint = input<GenerationCheckpoint | null>(null);
  readonly loading = input(false);

  readonly savedBatchCount = computed(() =>
    Object.values(this.checkpoint()?.entities ?? {}).reduce(
      (total, entity) => total + entity.completed_chunks.length,
      0,
    ),
  );

  readonly entityCount = computed(() =>
    Object.keys(this.checkpoint()?.entities ?? {}).length,
  );

  readonly entitiesWithSavedProgress = computed(() =>
    Object.values(this.checkpoint()?.entities ?? {}).filter(
      (entity) => entity.completed_chunks.length > 0,
    ).length,
  );

  readonly hasSavedProgress = computed(
    () => this.savedBatchCount() > 0,
  );
}
