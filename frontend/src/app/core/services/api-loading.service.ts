/**
 * File: api-loading.service.ts
 * Purpose: Track active FORGE API requests for global loading indicators.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class ApiLoadingService {
  private readonly activeRequestCount = signal(0);

  readonly isLoading = this.activeRequestCount.asReadonly();

  start(): void {
    this.activeRequestCount.update((count) => count + 1);
  }

  stop(): void {
    this.activeRequestCount.update((count) => Math.max(0, count - 1));
  }
}
