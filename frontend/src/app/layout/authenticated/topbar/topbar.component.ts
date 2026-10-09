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
  output,
  signal,
} from '@angular/core';

import { AuthService } from '../../../core/services/auth.service';
import { FormDialogComponent } from '../../../shared/components/form-dialog/form-dialog.component';

@Component({
  selector: 'app-forge-topbar',
  standalone: true,
  imports: [FormDialogComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.css',
})
export class TopbarComponent {
  readonly action = output<string>();
  readonly profileDialogOpen = signal(false);

  constructor(readonly authService: AuthService) {}

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
