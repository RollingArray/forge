import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { GenerationService } from '../generate/services/generation.service';
import { Favorite } from '../../core/interfaces/favorite.interface';
import { FavoritesService } from '../../core/services/favorites.service';
import { WorkspaceToolbarAction } from '../../shared/components/workspace-table-toolbar/workspace-table-toolbar.component';
import { GenerationArtifactDataPage } from '../results/results.models';
import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import {
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';
import { WorkspaceHeaderComponent } from '../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceTableToolbarComponent } from '../../shared/components/workspace-table-toolbar/workspace-table-toolbar.component';
import { WorkspaceSimpleTableComponent } from '../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkspaceSimpleTableColumn } from '../../shared/components/workspace-simple-table/workspace-simple-table.models';

@Component({
  selector: 'app-generated-file-data',
  standalone: true,
  imports: [
    CommonModule,
    WorkflowPageComponent,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceTableToolbarComponent,
    WorkspaceSimpleTableComponent,
  ],
  templateUrl: './generated-file-data.component.html',
  styleUrl: './generated-file-data.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GeneratedFileDataComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly generationService = inject(GenerationService);
  private readonly favoritesService = inject(FavoritesService);
  private readonly destroyRef = inject(DestroyRef);

  readonly dataModelId = this.route.snapshot.paramMap.get('dataModelId') ?? '';
  readonly jobId = this.route.snapshot.paramMap.get('jobId') ?? '';
  readonly entityName = this.route.snapshot.paramMap.get('entityName') ?? '';

  readonly page = signal<GenerationArtifactDataPage | null>(null);
  readonly isFavorite = signal(false);
  readonly favoriteId = signal<string | null>(null);
  readonly favoriteBusy = signal(false);
  readonly favoriteMessage = signal<string | null>(null);

  readonly toolbarActions = computed<readonly WorkspaceToolbarAction[]>(() => [
    {
      id: 'toggle-favorite',
      icon: this.isFavorite() ? 'bookmark_added' : 'bookmark_add',
      label: '',
      variant: this.isFavorite() ? 'default' : 'primary',
      disabled: this.favoriteBusy(),
      tooltip: this.isFavorite()
        ? `Remove ${this.entityName} from Favorites`
        : `Add ${this.entityName} to Favorites`,
    },
  ]);
  readonly steps: readonly WorkflowStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];
  readonly activeStep: WorkflowStep = 'results';

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly searchTerm = signal('');
  readonly offset = signal(0);
  readonly pageSize = signal(50);
  readonly pageSizes = [25, 50, 100, 200];

  readonly columns = computed<readonly WorkspaceSimpleTableColumn<Record<string, unknown>>[]>(() =>
    (this.page()?.columns ?? []).map((column) => ({
      key: column,
      label: column,
    })),
  );

  readonly rows = computed(() => this.page()?.rows ?? []);
  readonly rowKey = computed(() => this.page()?.columns[0] ?? '');
  readonly totalRows = computed(() => this.page()?.total_rows ?? 0);
  readonly currentPage = computed(() =>
    Math.floor(this.offset() / this.pageSize()) + 1,
  );
  readonly pageCount = computed(() =>
    Math.max(1, Math.ceil(this.totalRows() / this.pageSize())),
  );
  readonly canGoPrevious = computed(() => this.offset() > 0);
  readonly canGoNext = computed(
    () => this.offset() + this.rows().length < this.totalRows(),
  );

  constructor() {
    if (!this.dataModelId || !this.jobId || !this.entityName) {
      this.error.set('The generated file destination is incomplete.');
      return;
    }
    this.loadPage();
    this.loadFavoriteStatus();
  }

  handleToolbarAction(actionId: string): void {
    if (actionId === 'toggle-favorite') {
      this.addToFavorites();
    }
  }

  private loadFavoriteStatus(): void {
    this.favoritesService.getFavorites()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (favorites) => {
          const favorite = favorites.find((item) =>
            item.resource_type === 'generated_table'
            && item.data_model_id === this.dataModelId
            && item.job_id === this.jobId
            && item.entity_name === this.entityName
          ) ?? null;

          this.favoriteId.set(favorite?.favorite_id ?? null);
          this.isFavorite.set(favorite !== null);
        },
      });
  }

  private addToFavorites(): void {
    if (this.favoriteBusy()) {
      return;
    }

    this.favoriteBusy.set(true);
    this.favoriteMessage.set(null);

    const favoriteId = this.favoriteId();

    if (favoriteId) {
      this.favoritesService.removeFavorite(favoriteId)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.favoriteId.set(null);
            this.isFavorite.set(false);
            this.favoriteBusy.set(false);
            this.favoriteMessage.set(`${this.entityName} removed from Favorites.`);
          },
          error: () => {
            this.favoriteBusy.set(false);
            this.favoriteMessage.set('Could not update Favorites. Please try again.');
          },
        });
      return;
    }

    this.favoritesService.addFavorite({
      resource_type: 'generated_table',
      data_model_id: this.dataModelId,
      job_id: this.jobId,
      entity_name: this.entityName,
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (favorite: Favorite) => {
        this.favoriteId.set(favorite.favorite_id);
        this.isFavorite.set(true);
        this.favoriteBusy.set(false);
        this.favoriteMessage.set(`${this.entityName} saved to Favorites.`);
      },
      error: () => {
        this.favoriteBusy.set(false);
        this.favoriteMessage.set('Could not save to Favorites. Please try again.');
      },
    });
  }

  updateSearch(value: string): void {
    this.searchTerm.set(value);
    this.offset.set(0);
    this.loadPage();
  }

  changePageSize(value: string): void {
    const size = Number(value);
    if (!this.pageSizes.includes(size)) {
      return;
    }
    this.pageSize.set(size);
    this.offset.set(0);
    this.loadPage();
  }

  previousPage(): void {
    if (!this.canGoPrevious()) {
      return;
    }
    this.offset.set(Math.max(0, this.offset() - this.pageSize()));
    this.loadPage();
  }

  nextPage(): void {
    if (!this.canGoNext()) {
      return;
    }
    this.offset.update((value) => value + this.pageSize());
    this.loadPage();
  }

  selectStep(step: WorkflowStep): void {
    if (!this.dataModelId) {
      return;
    }

    switch (step) {
      case 'model':
        void this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'studio']);
        break;
      case 'validate':
        void this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'validation']);
        break;
      case 'population':
        void this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'population']);
        break;
      case 'generate':
        void this.router.navigate(['/workspace', this.dataModelId, 'data-model', 'generate']);
        break;
      case 'results':
        this.backToResults();
        break;
    }
  }

  backToResults(): void {
    void this.router.navigate([
      '/workspace',
      this.dataModelId,
      'data-model',
      'results',
      this.jobId,
    ]);
  }

  private loadPage(): void {
    this.loading.set(true);
    this.error.set(null);

    this.generationService.getGenerationArtifactData(
      this.dataModelId,
      this.jobId,
      this.entityName,
      this.offset(),
      this.pageSize(),
      this.searchTerm().trim(),
    ).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (page) => {
        this.page.set(page);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('The generated dataset could not be loaded.');
        this.loading.set(false);
      },
    });
  }
}
