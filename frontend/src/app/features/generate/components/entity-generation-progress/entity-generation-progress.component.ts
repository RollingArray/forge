import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';

import { GenerationEntityProgress } from '../../models/generation.models';

@Component({
  selector: 'app-entity-generation-progress',
  standalone: true,
  imports: [CommonModule, DecimalPipe],
  templateUrl: './entity-generation-progress.component.html',
  styleUrl: './entity-generation-progress.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityGenerationProgressComponent {
  readonly entities = input<GenerationEntityProgress[]>([]);
  readonly totalGeneratedRows = input(0);
  readonly totalTargetRows = input(0);

  progress(entity: GenerationEntityProgress): number {
    if (entity.total_chunks <= 0) {
      return 0;
    }

    return Math.min(
      Math.max(
        (entity.completed_chunks / entity.total_chunks) * 100,
        0,
      ),
      100,
    );
  }

  statusLabel(entity: GenerationEntityProgress): string {
    switch (entity.status) {
      case 'NOT_STARTED':
        return 'Waiting';
      case 'QUEUED':
        return 'Queued';
      case 'RUNNING':
        return 'Generating';
      case 'COMPLETED':
        return 'Completed';
      case 'FAILED':
        return 'Failed';
      case 'CANCELLED':
        return 'Cancelled';
      default:
        return entity.status;
    }
  }

  entityIcon(entityName: string): string {
    const name = entityName.toUpperCase();

    if (name.includes('CUSTOMER')) {
      return 'person';
    }

    if (name.includes('PRODUCT')) {
      return 'inventory_2';
    }

    if (name.includes('ORDER_LINE') || name.includes('ITEM')) {
      return 'description';
    }

    if (name.includes('ORDER')) {
      return 'shopping_cart';
    }

    if (name.includes('WAREHOUSE')) {
      return 'warehouse';
    }

    if (name.includes('SHIPMENT')) {
      return 'local_shipping';
    }

    if (name.includes('REGION')) {
      return 'flag';
    }

    if (name.includes('CHANNEL')) {
      return 'account_tree';
    }

    return 'table_rows';
  }

  chunkNumbers(entity: GenerationEntityProgress): number[] {
    const total = Math.max(entity.total_chunks, 0);

    if (total <= 6) {
      return Array.from({ length: total }, (_, index) => index + 1);
    }

    const currentChunk = Math.min(
      entity.completed_chunks + 1,
      total,
    );

    if (currentChunk <= 5) {
      return [1, 2, 3, 4, 5, total];
    }

    return [1, 2, 3, 4, 5, currentChunk];
  }

  isChunkCompleted(
    entity: GenerationEntityProgress,
    chunkNumber: number,
  ): boolean {
    return chunkNumber <= entity.completed_chunks;
  }

  isChunkRunning(
    entity: GenerationEntityProgress,
    chunkNumber: number,
  ): boolean {
    return (
      entity.status === 'RUNNING' &&
      chunkNumber === entity.completed_chunks + 1
    );
  }

  trackEntity(
    index: number,
    entity: GenerationEntityProgress,
  ): string {
    return entity.entity_name;
  }
}
