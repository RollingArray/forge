/**
 * File: topbar.component.ts
 * Purpose: Shared FORGE authenticated application topbar.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  output,
  signal,
} from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AuthService } from '../../../../core/services/auth.service';
import { FavoritesService } from '../../../../core/services/favorites.service';
import { Favorite } from '../../../../core/interfaces/favorite.interface';
import { ResourceReference } from '../../../../core/interfaces/resource-reference.interface';
import { RESOURCE_DEFINITIONS, resolveResourceReferenceFromUrl } from '../../../../core/registries/resource.registry';
import { UserProfileComponent } from '../../../../shared/components/user-profile/user-profile.component';
import { ForgeButtonComponent } from '../../../../shared/components/forge-button/forge-button.component';

@Component({
  selector: 'app-forge-topbar',
  standalone: true,
  imports: [UserProfileComponent, ForgeButtonComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.css',
})
export class TopbarComponent {
  readonly action = output<string>();
  readonly profileDialogOpen = signal(false);

  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly favoritesService = inject(FavoritesService);

  readonly currentResource = signal<ResourceReference | null>(null);
  readonly currentFavorite = signal<Favorite | null>(null);
  readonly favoriteBusy = signal(false);
  readonly favoriteMessage = signal<string | null>(null);

  constructor(readonly authService: AuthService) {
    this.refreshFavoriteState();

    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((event) => {
        this.refreshFavoriteState(event.urlAfterRedirects);
      });
  }

  get favoriteLabel(): string {
    const resource = this.currentResource();
    if (!resource) {
      return 'current resource';
    }

    return resource.resourceType === 'generated_table' && resource.entityName
      ? `${resource.entityName} Table`
      : RESOURCE_DEFINITIONS[resource.resourceType].label;
  }

  private refreshFavoriteState(url = this.router.url): void {
    const resource = resolveResourceReferenceFromUrl(url);
    this.currentResource.set(resource);
    this.currentFavorite.set(null);
    this.favoriteMessage.set(null);

    if (!resource) {
      return;
    }

    this.favoritesService.getFavorites()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (favorites) => {
          // Ignore a response if navigation has moved to another resource.
          if (this.currentResource() !== resource &&
              (this.currentResource()?.resourceType !== resource.resourceType ||
               this.currentResource()?.dataModelId !== resource.dataModelId ||
               this.currentResource()?.jobId !== resource.jobId ||
               this.currentResource()?.entityName !== resource.entityName)) {
            return;
          }

          this.currentFavorite.set(
            favorites.find((favorite) =>
              favorite.resource_type === resource.resourceType &&
              favorite.data_model_id === resource.dataModelId &&
              (favorite.job_id ?? undefined) === resource.jobId &&
              (resource.resourceType !== 'generated_table' ||
                favorite.entity_name === resource.entityName),
            ) ?? null,
          );
        },
        error: () => {
          this.favoriteMessage.set('Could not load Favorites status.');
        },
      });
  }

  toggleFavorite(): void {
    const resource = this.currentResource();

    if (!resource || this.favoriteBusy()) {
      return;
    }

    this.favoriteBusy.set(true);
    this.favoriteMessage.set(null);

    const existing = this.currentFavorite();

    if (existing) {
      this.favoritesService.removeFavorite(existing.favorite_id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.currentFavorite.set(null);
            this.favoriteMessage.set(
              `${this.favoriteLabel} removed from Favorites.`,
            );
            this.favoriteBusy.set(false);
          },
          error: () => {
            this.favoriteBusy.set(false);
            this.favoriteMessage.set(
              'Could not update Favorites. Please try again.',
            );
          },
        });

      return;
    }

    this.favoritesService.addFavorite({
      resource_type: resource.resourceType,
      data_model_id: resource.dataModelId,
      ...(resource.jobId ? { job_id: resource.jobId } : {}),
      ...(resource.entityName ? { entity_name: resource.entityName } : {}),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (favorite: Favorite) => {
          this.currentFavorite.set(favorite);
          this.favoriteMessage.set(
            `${this.favoriteLabel} added to Favorites.`,
          );
          this.favoriteBusy.set(false);
        },
        error: () => {
          this.favoriteBusy.set(false);
          this.favoriteMessage.set(
            'Could not update Favorites. Please try again.',
          );
        },
      });
  }

  get currentUser() {
    return this.authService.getSession()?.user ?? null;
  }

  get adProfile(): Record<string, unknown> | null {
    const profile = this.currentUser?.profile;

    if (!profile) {
      return null;
    }

    const nested = profile['ad_profile'];

    if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
      return nested as Record<string, unknown>;
    }

    return profile;
  }

  profileValue(key: string): string | null {
    const value = this.adProfile?.[key];

    return typeof value === 'string' && value.trim()
      ? value.trim()
      : null;
  }

  get initials(): string {
    const firstName = this.profileValue('firstName');
    const lastName = this.profileValue('lastName');

    if (firstName || lastName) {
      return `${firstName?.[0] ?? ''}${lastName?.[0] ?? ''}`.toUpperCase();
    }

    // Fallback for sessions without an AD profile.
    const displayName = this.currentUser?.displayName?.trim() ?? '';

    if (displayName.includes(',')) {
      const [last, ...givenParts] = displayName.split(',');
      const first = givenParts.join(',').trim().split(/\\s+/)[0] ?? '';

      return `${first[0] ?? ''}${last.trim()[0] ?? ''}`.toUpperCase();
    }

    const parts = displayName.split(/\\s+/).filter(Boolean);

    if (parts.length > 1) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
    }

    return displayName.slice(0, 2).toUpperCase() || '?';
  }

  openProfile(): void {
    this.profileDialogOpen.set(true);
  }

  closeProfile(): void {
    this.profileDialogOpen.set(false);
  }

  select(action: string): void {
    this.action.emit(action);
  }
}
