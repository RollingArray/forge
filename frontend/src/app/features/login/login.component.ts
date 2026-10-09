import { HttpErrorResponse } from '@angular/common/http';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LoginShellComponent } from './components/login-shell/login-shell.component';
import { MagicLinkService } from '../../core/services/magic-link.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, LoginShellComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
  readonly email = signal('');
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly linkSent = signal(false);

  constructor(private readonly magicLinkService: MagicLinkService) {}

  async continue(): Promise<void> {
    const value = this.email().trim();

    if (!value || this.isLoading() || this.linkSent()) {
      return;
    }

    this.errorMessage.set('');
    this.isLoading.set(true);

    try {
      await this.magicLinkService.requestLink(value);
      this.linkSent.set(true);
    } catch (error) {
      console.error('FORGE magic-link request failed:', error);

      if (
        error instanceof HttpErrorResponse &&
        error.status === 403
      ) {
        this.errorMessage.set(
          'Please use an email address from your organization.',
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
          'Unable to send the sign-in link. Please try again.',
        );
      }
    } finally {
      this.isLoading.set(false);
    }
  }

  useDifferentEmail(): void {
    this.linkSent.set(false);
    this.errorMessage.set('');
  }

  toggleTheme(): void {
    console.log('FORGE theme toggle');
  }
}
