import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { DatePipe, UpperCasePipe } from '@angular/common';
import { Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { WorkflowPageHeaderComponent } from '../../shared/components/workflow-page-header/workflow-page-header.component';
import { WorkflowContentComponent } from '../../shared/components/workflow-content/workflow-content.component';
import { ContentGridComponent } from '../../shared/components/content-grid/content-grid.component';
import { WorkspaceSectionComponent } from '../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../shared/components/workspace-header/workspace-header.component';
import { FavoriteCardComponent } from './components/favorite-card/favorite-card.component';
import { FavoritesCollectionToolbarComponent } from './components/favorites-collection-toolbar/favorites-collection-toolbar.component';
import { ContentCardComponent } from '../../shared/components/content-card/content-card.component';
import { FavoritesService } from '../../core/services/favorites.service';
import { Favorite } from '../../core/interfaces/favorite.interface';
import { ResourceReference } from '../../core/interfaces/resource-reference.interface';
import {
  RESOURCE_DEFINITIONS,
  resolveResourceRoute,
} from '../../core/registries/resource.registry';
import { WorkflowRowComponent } from '../../shared/components/workflow-row/workflow-row.component';

@Component({
  selector: 'app-favorites',
  standalone: true,
  imports: [
    DatePipe,
    UpperCasePipe,
    WorkflowPageHeaderComponent,
    WorkflowContentComponent,
    ContentGridComponent,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    FavoriteCardComponent,
    FavoritesCollectionToolbarComponent,
    ContentCardComponent,
    WorkflowRowComponent,
  ],
  templateUrl: './favorites.component.html',
  styleUrl: './favorites.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FavoritesComponent {
  private readonly favoritesService = inject(FavoritesService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly favorites = signal<Favorite[]>([]);
  readonly searchQuery = signal('');
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly removingFavoriteId = signal<string | null>(null);
  readonly resourceDefinitions = RESOURCE_DEFINITIONS;

  readonly categories = [
    {
      id: 'model-design',
      title: 'Model Design',
      description: 'Define and validate your model specification.',
      icon: 'account_tree',
      resourceTypes: ['model_studio', 'model_validation'],
    },
    {
      id: 'planning',
      title: 'Planning',
      description: 'Prepare entity populations before generation.',
      icon: 'groups',
      resourceTypes: ['population_plan'],
    },
    {
      id: 'generation',
      title: 'Generation',
      description: 'Start generation or revisit an execution.',
      icon: 'play_circle',
      resourceTypes: ['generation', 'generation_execution'],
    },
    {
      id: 'results-analysis',
      title: 'Results & Analysis',
      description: 'Review generated data and quality findings.',
      icon: 'analytics',
      resourceTypes: ['generation_results', 'generated_table', 'validation_analysis', 'quality_analysis'],
    },
  ] as const;

  filteredFavorites(): Favorite[] {
    const query = this.searchQuery().trim().toLocaleLowerCase();

    if (!query) {
      return this.favorites();
    }

    return this.favorites().filter((favorite) => {
      const resourceLabel = RESOURCE_DEFINITIONS[favorite.resource_type]?.label ?? '';
      const searchableText = [
        resourceLabel,
        favorite.data_model_name,
        favorite.entity_name,
        favorite.job_id,
        favorite.status,
        favorite.resource_type,
      ]
        .filter(Boolean)
        .join(' ')
        .toLocaleLowerCase();

      return searchableText.includes(query);
    });
  }

  favoritesFor(resourceTypes: readonly string[]): Favorite[] {
    return this.filteredFavorites().filter((favorite) =>
      resourceTypes.includes(favorite.resource_type),
    );
  }

  constructor() {
    this.loadFavorites();
  }

  loadFavorites(): void {
    this.loading.set(true);
    this.error.set(null);

    this.favoritesService
      .getFavorites()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (favorites) => {
          this.favorites.set(favorites);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('Favorites could not be loaded. Please try again.');
          this.loading.set(false);
        },
      });
  }

  routerNavigateWorkspace(): void {
    void this.router.navigate(['/workspace']);
  }

  openFavorite(favorite: Favorite): void {
    const reference: ResourceReference = {
      resourceType: favorite.resource_type,
      dataModelId: favorite.data_model_id,
      ...(favorite.job_id ? { jobId: favorite.job_id } : {}),
      ...(favorite.entity_name ? { entityName: favorite.entity_name } : {}),
    };
    const route = resolveResourceRoute(reference);

    if (!route) {
      this.error.set('This favorite does not have a valid destination.');
      return;
    }

    void this.router.navigate(route);
  }

  removeFavorite(favorite: Favorite): void {
    if (this.removingFavoriteId()) {
      return;
    }

    this.removingFavoriteId.set(favorite.favorite_id);

    this.favoritesService
      .removeFavorite(favorite.favorite_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.favorites.update((items) =>
            items.filter((item) => item.favorite_id !== favorite.favorite_id),
          );
          this.removingFavoriteId.set(null);
        },
        error: () => {
          this.error.set('The favorite could not be removed. Please try again.');
          this.removingFavoriteId.set(null);
        },
      });
  }

  trackFavorite(_index: number, favorite: Favorite): string {
    return favorite.favorite_id;
  }
}
