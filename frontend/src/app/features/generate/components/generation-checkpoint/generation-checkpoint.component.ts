import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  GenerationCheckpoint,
  GenerationCheckpointLiveProgress,
} from '../../../../core/interfaces/generation-checkpoint.interface';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';


@Component({
  selector: 'app-generation-checkpoint',
  standalone: true,
  imports: [CommonModule, WorkspaceSectionComponent, WorkspaceHeaderComponent],
  templateUrl: './generation-checkpoint.component.html',
  styleUrl: './generation-checkpoint.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationCheckpointComponent {
  readonly checkpoint = input<GenerationCheckpoint | null>(null);
  readonly liveProgress = input<GenerationCheckpointLiveProgress | null>(null);
  readonly loading = input(false);
  readonly canResume = input(false);
  readonly resuming = input(false);
  readonly resumeRequested = output<void>();

  readonly savedBatchCount = computed(() => {
    const live = this.liveProgress();

    if (live) {
      return Object.values(live.entities).reduce(
        (total, entity) => total + entity.saved_chunks,
        0,
      );
    }

    return Object.values(this.checkpoint()?.entities ?? {}).reduce(
      (total, entity) => total + entity.chunks.length,
      0,
    );
  });

  readonly entityCount = computed(() =>
    Object.keys(
      this.liveProgress()?.entities ??
      this.checkpoint()?.entities ??
      {},
    ).length,
  );

  readonly entitiesWithSavedProgress = computed(() => {
    const live = this.liveProgress();

    if (live) {
      return Object.values(live.entities).filter(
        (entity) => entity.saved_chunks > 0,
      ).length;
    }

    return Object.values(this.checkpoint()?.entities ?? {}).filter(
      (entity) => entity.chunks.length > 0,
    ).length;
  });

  readonly lastSavedAt = computed(
    () => this.liveProgress()?.updated_at ?? this.checkpoint()?.updated_at ?? null,
  );

  readonly hasSavedProgress = computed(() => this.savedBatchCount() > 0);
}
