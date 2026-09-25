/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: authenticated-layout.component.ts
 * Purpose: Shared authenticated application layout for FORGE.
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
} from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ApiLoadingService } from '../../core/services/api-loading.service';

import {
  ApiLoadingSpinnerComponent,
} from './components/api-loading-spinner/api-loading-spinner.component';
import {
  TechnicalDataBannerComponent,
} from './components/technical-data-banner/technical-data-banner.component';

import { SidebarComponent } from './sidebar/sidebar.component';
import { TopbarComponent } from './topbar/topbar.component';

@Component({
  selector: 'app-authenticated-layout',
  standalone: true,
  imports: [
    TechnicalDataBannerComponent,
    RouterOutlet,
    ApiLoadingSpinnerComponent,
    SidebarComponent,
    TopbarComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './authenticated-layout.component.html',
  styleUrl: './authenticated-layout.component.css',
})
export class AuthenticatedLayoutComponent {
  readonly apiLoadingService = inject(ApiLoadingService);
  handleSidebarAction(action: string): void {
    console.info('[FORGE Navigation] sidebar action:', action);
  }

  handleTopbarAction(action: string): void {
    console.info('[FORGE Navigation] topbar action:', action);
  }
}
