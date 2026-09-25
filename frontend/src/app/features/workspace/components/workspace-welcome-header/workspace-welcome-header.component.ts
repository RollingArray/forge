/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: workspace-welcome-header.component.ts
 * Purpose: Defines the workspace welcome header Workspace component.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  inject,
  output,
  signal,
} from '@angular/core';

import { AuthService } from '../../../../core/services/auth.service';


@Component({
  selector: 'app-workspace-welcome-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workspace-welcome-header.component.html',
  styleUrl: './workspace-welcome-header.component.css',
})
export class WorkspaceWelcomeHeaderComponent {
  private readonly authService = inject(AuthService);

  readonly currentUser = this.authService.getSession()?.user;

  readonly greeting = signal(this.getGreeting());

  private getGreeting(): string {
    const hour = new Date().getHours();

    if (hour < 12) {
      return 'Good morning';
    }

    if (hour < 18) {
      return 'Good afternoon';
    }

    return 'Good evening';
  }

  readonly newDataModel = output<void>();

  createDataModel(): void {
    this.newDataModel.emit();
  }
}
