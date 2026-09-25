import { AuthService } from '../../../../core/services/auth.service';
/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: data-model-share-dialog.component.ts
 * Purpose: Defines the Data Model sharing dialog.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  computed,
  Component,
  DestroyRef,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  Subject,
  catchError,
  debounceTime,
  distinctUntilChanged,
  of,
  switchMap,
  tap,
} from 'rxjs';

import { DataModel } from '../../../../core/interfaces/data-model.interface';
import { DataModelAccess } from '../../../../core/interfaces/data-model-access.interface';
import { DataModelAccessService } from '../../../../core/services/data-model-access.service';
import { UserSearchResult } from '../../../../core/interfaces/user-search-result.interface';
import { UserService } from '../../../../core/services/user.service';
import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';

@Component({
  selector: 'app-data-model-share-dialog',
  standalone: true,
  imports: [
    FormDialogComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './data-model-share-dialog.component.html',
  styleUrl: './data-model-share-dialog.component.css',
})
export class DataModelShareDialogComponent {
  readonly dataModel = input.required<DataModel>();

  readonly isOwner = computed(() => {
    const session = this.authService.getSession();

    return (
      session?.user.userId === this.dataModel().ownerUserId
    );
  });

  readonly closed = output<void>();

  readonly searchQuery = signal('');
  readonly searchResults = signal<UserSearchResult[]>([]);
  readonly searching = signal(false);
  readonly searchCompleted = signal(false);

  readonly selectedUser = signal<UserSearchResult | null>(null);
  readonly selectedRole = signal<'CONTRIBUTOR' | 'VIEWER'>('CONTRIBUTOR');
  readonly addingAccess = signal(false);
  readonly addAccessError = signal(false);
  readonly accessRecords = signal<DataModelAccess[]>([]);
  readonly loadingAccess = signal(false);
  readonly accessLoadError = signal(false);
  readonly updatingAccessUserId = signal<string | null>(null);
  readonly updateAccessError = signal(false);

  readonly confirmation = signal<{
    action: 'ROLE_CHANGE' | 'REMOVE_ACCESS';
    access: DataModelAccess;
    role?: 'CONTRIBUTOR' | 'VIEWER';
  } | null>(null);

  private readonly authService = inject(AuthService);
  private readonly userService = inject(UserService);
  private readonly dataModelAccessService = inject(DataModelAccessService);
  private readonly destroyRef = inject(DestroyRef);

  private readonly searchInput$ = new Subject<string>();

  constructor() {
    effect(() => {
      const dataModel = this.dataModel();

      if (dataModel.dataModelId) {
        this.loadAccess();
      }
    });

    this.searchInput$
      .pipe(
        debounceTime(250),
        distinctUntilChanged(),
        tap((query) => {
          this.searchCompleted.set(false);

          if (!query) {
            this.searchResults.set([]);
            this.searching.set(false);
          } else {
            this.searching.set(true);
          }
        }),
        switchMap((query) => {
          if (!query) {
            return of([]);
          }

          return this.userService.searchUsers(query).pipe(
            catchError(() => of([])),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((results) => {
        this.searchResults.set(results);
        this.searching.set(false);
        this.searchCompleted.set(true);
      });
  }

  private loadAccess(): void {
    this.loadingAccess.set(true);
    this.accessLoadError.set(false);

    this.dataModelAccessService
      .getAccess(this.dataModel().dataModelId)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (accessRecords) => {
          this.accessRecords.set(accessRecords);
          this.loadingAccess.set(false);
        },
        error: () => {
          this.accessRecords.set([]);
          this.loadingAccess.set(false);
          this.accessLoadError.set(true);
        },
      });
  }

  onSearchInput(value: string): void {
    const query = value.trim();

    this.searchQuery.set(query);
    this.selectedUser.set(null);
    this.searchInput$.next(query);
  }

  selectUser(user: UserSearchResult): void {
    this.selectedUser.set(user);
    this.selectedRole.set('CONTRIBUTOR');
  }

  selectRole(role: 'CONTRIBUTOR' | 'VIEWER'): void {
    this.selectedRole.set(role);
  }

  addAccess(): void {
    const user = this.selectedUser();

    if (!user || this.addingAccess()) {
      return;
    }

    this.addAccessError.set(false);
    this.addingAccess.set(true);

    this.dataModelAccessService
      .grantAccess(
        this.dataModel().dataModelId,
        user.userId,
        this.selectedRole(),
      )
      .pipe(
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.addingAccess.set(false);
          this.selectedUser.set(null);
          this.searchQuery.set('');
          this.searchResults.set([]);
          this.searchCompleted.set(false);
          this.loadAccess();
        },
        error: () => {
          this.addingAccess.set(false);
          this.addAccessError.set(true);
        },
      });
  }

  requestRoleChange(
    access: DataModelAccess,
    role: 'CONTRIBUTOR' | 'VIEWER',
  ): void {
    if (
      !this.isOwner() ||
      access.role === 'OWNER' ||
      access.role === role ||
      this.updatingAccessUserId()
    ) {
      return;
    }

    this.confirmation.set({
      action: 'ROLE_CHANGE',
      access,
      role,
    });
  }

  requestRemoveAccess(access: DataModelAccess): void {
    if (
      !this.isOwner() ||
      access.role === 'OWNER' ||
      this.updatingAccessUserId()
    ) {
      return;
    }

    this.confirmation.set({
      action: 'REMOVE_ACCESS',
      access,
    });
  }

  cancelAccessAction(): void {
    this.confirmation.set(null);
  }

  confirmAccessAction(): void {
    const confirmation = this.confirmation();

    if (!confirmation || this.updatingAccessUserId()) {
      return;
    }

    const access = confirmation.access;

    this.confirmation.set(null);
    this.updateAccessError.set(false);
    this.updatingAccessUserId.set(access.userId);

    if (confirmation.action === 'ROLE_CHANGE' && confirmation.role) {
      this.dataModelAccessService
        .updateRole(
          this.dataModel().dataModelId,
          access.userId,
          confirmation.role,
        )
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.updatingAccessUserId.set(null);
            this.loadAccess();
          },
          error: () => {
            this.updatingAccessUserId.set(null);
            this.updateAccessError.set(true);
          },
        });

      return;
    }

    this.dataModelAccessService
      .revokeAccess(
        this.dataModel().dataModelId,
        access.userId,
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.updatingAccessUserId.set(null);
          this.loadAccess();
        },
        error: () => {
          this.updatingAccessUserId.set(null);
          this.updateAccessError.set(true);
        },
      });
  }


  close(): void {
    this.closed.emit();
  }
}
