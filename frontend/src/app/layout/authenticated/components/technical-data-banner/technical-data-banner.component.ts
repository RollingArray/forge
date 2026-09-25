/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: technical-data-banner.component.ts
 * Purpose: Displays the enterprise technical-data handling banner.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';

@Component({
  selector: 'app-technical-data-banner',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './technical-data-banner.component.html',
  styleUrl: './technical-data-banner.component.css',
})
export class TechnicalDataBannerComponent {}
