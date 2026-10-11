/**
 * File: user-profile.component.ts
 * Purpose: Shared authenticated FORGE user profile dialog.
 */

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { AuthService } from '../../../core/services/auth.service';
import { FormDialogComponent } from '../form-dialog/form-dialog.component';

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [FormDialogComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './user-profile.component.html',
  styleUrl: './user-profile.component.css',
})
export class UserProfileComponent {
  readonly open = input(false);
  readonly closed = output<void>();

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

    if (firstName && lastName) {
      return `${firstName[0]}${lastName[0]}`.toUpperCase();
    }

    const displayName = this.currentUser?.displayName?.trim() ?? '';

    if (displayName.includes(',')) {
      const [last, ...givenParts] = displayName.split(',');
      const first = givenParts.join(',').trim().split(/\s+/)[0] ?? '';
      const surname = last.trim();

      return `${first[0] ?? ''}${surname[0] ?? ''}`.toUpperCase() || '?';
    }

    if (firstName || lastName) {
      return `${firstName?.[0] ?? ''}${lastName?.[0] ?? ''}`.toUpperCase();
    }

    const parts = displayName.split(/\s+/).filter(Boolean);

    if (parts.length > 1) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
    }

    return displayName.slice(0, 2).toUpperCase() || '?';
  }

  closeProfile(): void {
    this.closed.emit();
  }
}
