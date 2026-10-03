import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  QueryList,
  ViewChildren,
  input,
  signal,
} from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';

import {
  GenerationEntityProgress,
  GenerationSemanticCallStartedEvent,
} from '../../models/generation.models';

import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceTableComponent } from '../../../../shared/components/workspace-table/workspace-table.component';

@Component({
  selector: 'app-entity-generation-progress',
  standalone: true,
  imports: [
    CommonModule,
    DecimalPipe,
    WorkspaceHeaderComponent,
    WorkspaceTableComponent,
  ],
  templateUrl: './entity-generation-progress.component.html',
  styleUrl: './entity-generation-progress.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityGenerationProgressComponent
  implements AfterViewInit, OnDestroy {
  @ViewChildren('chunkList', { read: ElementRef })
  private readonly chunkLists!: QueryList<ElementRef<HTMLElement>>;

  private readonly chunkListWidths = signal<number[]>([]);
  private readonly resizeObservers = new Map<Element, ResizeObserver>();
  readonly entities = input<GenerationEntityProgress[]>([]);
  readonly totalGeneratedRows = input(0);
  readonly totalTargetRows = input(0);
  readonly activeSemanticCall = input<GenerationSemanticCallStartedEvent | null>(null);

  isSemanticActive(entity: GenerationEntityProgress): boolean {
    const call = this.activeSemanticCall();

    return call?.entity_name === entity.entity_name;
  }

  semanticFieldLabel(entity: GenerationEntityProgress): string | null {
    const call = this.activeSemanticCall();

    if (call?.entity_name !== entity.entity_name) {
      return null;
    }

    return call.field_name
      .toLowerCase()
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }

  semanticRequestedCount(entity: GenerationEntityProgress): number | null {
    const call = this.activeSemanticCall();

    if (call?.entity_name !== entity.entity_name) {
      return null;
    }

    return call.requested_count;
  }

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

  chunkNumbers(
    entity: GenerationEntityProgress,
    entityIndex: number,
  ): number[] {
    const total = Math.max(entity.total_chunks, 0);

    if (total <= 0) {
      return [];
    }

    const width = this.chunkListWidths()[entityIndex] ?? 0;

    if (width <= 0) {
      return [1];
    }

    const indicatorWidth = 18;
    const gap = 8;
    const ellipsisWidth = 14;

    const maxIndicators = Math.max(
      3,
      Math.floor((width + gap) / (indicatorWidth + gap)),
    );

    if (total <= maxIndicators) {
      return Array.from(
        { length: total },
        (_, index) => index + 1,
      );
    }

    const currentChunk = Math.min(
      Math.max(entity.completed_chunks + 1, 1),
      total,
    );

    const availableForIndicators =
      width - (ellipsisWidth * 2) - (gap * 2);

    const visibleIndicatorCount = Math.max(
      3,
      Math.floor(
        (availableForIndicators + gap) /
        (indicatorWidth + gap),
      ),
    );

    const chunks = new Set<number>();

    const addRange = (start: number, end: number): void => {
      for (let chunk = start; chunk <= end; chunk += 1) {
        chunks.add(chunk);
      }
    };

    /*
     * Always preserve:
     *   - the beginning of the sequence
     *   - the currently running chunk
     *   - the final chunk
     */
    chunks.add(1);
    chunks.add(currentChunk);
    chunks.add(total);

    let remaining = visibleIndicatorCount - chunks.size;

    /*
     * Fill from the beginning first so the sequence remains
     * recognizable, while never consuming the active/final slots.
     */
    for (let chunk = 2; chunk < currentChunk && remaining > 0; chunk += 1) {
      if (!chunks.has(chunk)) {
        chunks.add(chunk);
        remaining -= 1;
      }
    }

    /*
     * If there is still room, fill backwards from the end so
     * the final section of the sequence remains visible too.
     */
    for (
      let chunk = total - 1;
      chunk > currentChunk && remaining > 0;
      chunk -= 1
    ) {
      if (!chunks.has(chunk)) {
        chunks.add(chunk);
        remaining -= 1;
      }
    }

    return [...chunks].sort((a, b) => a - b);
  }

  hasChunkGap(
    chunks: number[],
    index: number,
  ): boolean {
    if (index === 0) {
      return false;
    }

    return chunks[index] > chunks[index - 1] + 1;
  }

  ngAfterViewInit(): void {
    this.observeChunkLists();

    this.chunkLists.changes.subscribe(() => {
      this.observeChunkLists();
    });
  }

  ngOnDestroy(): void {
    for (const observer of this.resizeObservers.values()) {
      observer.disconnect();
    }

    this.resizeObservers.clear();
  }

  private observeChunkLists(): void {
    const widths = this.chunkLists
      .toArray()
      .map((elementRef) => elementRef.nativeElement.clientWidth);

    this.chunkListWidths.set(widths);

    for (const observer of this.resizeObservers.values()) {
      observer.disconnect();
    }

    this.resizeObservers.clear();

    this.chunkLists.forEach((elementRef, index) => {
      const element = elementRef.nativeElement;

      const observer = new ResizeObserver((entries) => {
        const width = entries[0]?.contentRect.width;

        if (width == null) {
          return;
        }

        this.chunkListWidths.update((current) => {
          const next = [...current];

          while (next.length <= index) {
            next.push(0);
          }

          next[index] = width;
          return next;
        });
      });

      observer.observe(element);
      this.resizeObservers.set(element, observer);
    });
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
