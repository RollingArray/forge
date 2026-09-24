/**
 * File: login.component.ts
 * Purpose: FORGE Login page presentation and user interaction handling.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { HttpErrorResponse } from '@angular/common/http';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
  readonly email = signal('');
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router,
  ) {}

  async continue(): Promise<void> {
    const value = this.email().trim();

    if (!value || this.isLoading()) {
      return;
    }

    this.errorMessage.set('');
    this.isLoading.set(true);

    try {
      await this.authService.login({
        email: value,
      });

      await this.router.navigate(['/home']);
    } catch (error) {
      console.error('FORGE login failed:', error);

      if (
        error instanceof HttpErrorResponse &&
        error.status === 403
      ) {
        this.errorMessage.set(
          'Unable to sign in. Please use your organization email address.',
        );
      } else if (
        error instanceof HttpErrorResponse &&
        error.status === 0
      ) {
        this.errorMessage.set(
          'Unable to connect to FORGE. Please try again.',
        );
      } else {
        this.errorMessage.set(
          'Unable to sign in. Please try again.',
        );
      }
    } finally {
      this.isLoading.set(false);
    }
  }

  toggleTheme(): void {
    console.log('FORGE theme toggle');
  }
}
