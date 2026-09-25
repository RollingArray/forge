/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: api-loading-spinner.component.ts
 * Purpose: Displays the global FORGE API loading indicator.
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

import { ApiLoadingService } from '../../../../core/services/api-loading.service';

@Component({
  selector: 'app-api-loading-spinner',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './api-loading-spinner.component.html',
  styleUrl: './api-loading-spinner.component.css',
})
export class ApiLoadingSpinnerComponent {
  readonly apiLoadingService = inject(ApiLoadingService);
}
