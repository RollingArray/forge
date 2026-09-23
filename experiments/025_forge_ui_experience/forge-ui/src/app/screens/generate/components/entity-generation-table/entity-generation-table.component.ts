import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  signal,
} from '@angular/core';

import { EntityGenerationRow } from '../../models/generate.models';

@Component({
  selector: 'app-entity-generation-table',
  standalone: true,
  templateUrl: './entity-generation-table.component.html',
  styleUrl: './entity-generation-table.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityGenerationTableComponent {
  readonly rows =
    input.required<readonly EntityGenerationRow[]>();

  readonly page =
    signal(0);

  readonly pageSize = 10;

  readonly pageCount = computed(() =>
    Math.max(
      1,
      Math.ceil(
        this.rows().length /
          this.pageSize,
      ),
    ),
  );

  readonly visibleRows = computed(() => {
    const start =
      this.page() * this.pageSize;

    return this.rows().slice(
      start,
      start + this.pageSize,
    );
  });

  previousPage(): void {
    this.page.update(value =>
      Math.max(0, value - 1),
    );
  }

  nextPage(): void {
    this.page.update(value =>
      Math.min(
        this.pageCount() - 1,
        value + 1,
      ),
    );
  }

  visibleEnd(): number {
    return Math.min(
      (this.page() + 1) * this.pageSize,
      this.rows().length,
    );
  }

  format(value: number): string {
    return value.toLocaleString();
  }
}
