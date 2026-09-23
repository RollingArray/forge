import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  signal,
} from '@angular/core';

import { ResultsEntity } from '../../models/results.models';

@Component({
  selector: 'app-generated-dataset',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './generated-dataset.component.html',
  styleUrl: './generated-dataset.component.css',
})
export class GeneratedDatasetComponent {
  readonly entities =
    input.required<readonly ResultsEntity[]>();

  readonly pageSize = 10;

  readonly page = signal(0);

  readonly searchTerm = signal('');

  readonly filteredEntities = computed(() => {
    const search =
      this.searchTerm()
        .trim()
        .toLowerCase();

    if (!search) {
      return this.entities();
    }

    return this.entities().filter(
      entity =>
        entity.name
          .toLowerCase()
          .includes(search) ||
        entity.outputFile
          .toLowerCase()
          .includes(search),
    );
  });

  readonly visibleEntities = computed(() => {
    const start =
      this.page() * this.pageSize;

    return this.filteredEntities().slice(
      start,
      start + this.pageSize,
    );
  });

  readonly pageCount = computed(() =>
    Math.max(
      1,
      Math.ceil(
        this.filteredEntities().length /
          this.pageSize,
      ),
    ),
  );

  readonly pageNumbers = computed(() =>
    Array.from(
      { length: this.pageCount() },
      (_, index) => index + 1,
    ),
  );

  updateSearch(value: string): void {
    this.searchTerm.set(value);
    this.page.set(0);
  }

  previousPage(): void {
    this.page.update(
      current => Math.max(0, current - 1),
    );
  }

  nextPage(): void {
    this.page.update(
      current =>
        Math.min(
          this.pageCount() - 1,
          current + 1,
        ),
    );
  }

  selectPage(page: number): void {
    this.page.set(page - 1);
  }

  download(entity: ResultsEntity): void {
    console.info(
      '[FORGE Results] entity download requested:',
      entity.outputFile,
    );
  }

  menu(entity: ResultsEntity): void {
    console.info(
      '[FORGE Results] entity actions requested:',
      entity.name,
    );
  }

  visibleStart(): number {
    const total =
      this.filteredEntities().length;

    if (total === 0) {
      return 0;
    }

    return this.page() *
      this.pageSize +
      1;
  }

  visibleEnd(): number {
    return Math.min(
      (this.page() + 1) *
        this.pageSize,
      this.filteredEntities().length,
    );
  }
}
