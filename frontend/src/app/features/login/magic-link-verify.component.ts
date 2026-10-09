import { HttpErrorResponse } from '@angular/common/http';
import { Component, signal } from '@angular/core';
import { LoginShellComponent } from './components/login-shell/login-shell.component';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';
import { MagicLinkService } from '../../core/services/magic-link.service';

@Component({
  selector: 'app-magic-link-verify',
  standalone: true,
  imports: [LoginShellComponent],
  templateUrl: './magic-link-verify.component.html',
  styleUrl: './login.component.css',
})
export class MagicLinkVerifyComponent {
  readonly isVerifying = signal(true);
  readonly errorMessage = signal('');

  constructor(
    route: ActivatedRoute,
    private readonly magicLinkService: MagicLinkService,
    private readonly authService: AuthService,
    private readonly router: Router,
  ) {
    const token = route.snapshot.queryParamMap.get('token');

    if (!token) {
      this.isVerifying.set(false);
      this.errorMessage.set(
        'This sign-in link is missing its verification token. Request a new link.',
      );
      return;
    }

    void this.verify(token);
  }

  private async verify(token: string): Promise<void> {
    try {
      const session = await this.magicLinkService.verifyToken(token);

      // Persist the session only after the backend has verified the link
      // and completed its AD profile lookup.
      this.authService.acceptSession(session);
      await this.router.navigate(['/workspace']);
    } catch (error) {
      console.error('FORGE magic-link verification failed:', error);
      this.isVerifying.set(false);

      if (error instanceof HttpErrorResponse && error.status === 502) {
        this.errorMessage.set(
          'We could not retrieve your organization profile. Please try again shortly.',
        );
      } else if (
        error instanceof HttpErrorResponse &&
        [400, 401, 403, 404].includes(error.status)
      ) {
        this.errorMessage.set(
          'This sign-in link is invalid or has expired. Please request a new one.',
        );
      } else if (
        error instanceof HttpErrorResponse &&
        error.status === 0
      ) {
        this.errorMessage.set(
          'Unable to connect to FORGE. Check your connection and try again.',
        );
      } else {
        this.errorMessage.set(
          'We could not complete sign-in. Please request a new link and try again.',
        );
      }
    }
  }

  requestNewLink(): void {
    void this.router.navigate(['/login']);
  }
}
