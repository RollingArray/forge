/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: api-loading.service.ts
 * Purpose: Provides application-wide API loading state and messages.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { Injectable, signal } from '@angular/core';

import { ApiLoadingMessage } from '../enums/api-loading-message.enum';

@Injectable({
  providedIn: 'root',
})
export class ApiLoadingService {
  private readonly activeRequestCount = signal(0);
  private readonly activeMessages = signal<ApiLoadingMessage[]>([]);

  readonly isLoading = this.activeRequestCount.asReadonly();

  readonly message = signal<ApiLoadingMessage>(
    ApiLoadingMessage.Loading,
  );

  start(message: ApiLoadingMessage = ApiLoadingMessage.Loading): void {
    this.activeRequestCount.update((count) => count + 1);
    this.activeMessages.update((messages) => [...messages, message]);
    this.message.set(message);
  }

  stop(message: ApiLoadingMessage = ApiLoadingMessage.Loading): void {
    this.activeRequestCount.update((count) => Math.max(0, count - 1));

    this.activeMessages.update((messages) => {
      const index = messages.lastIndexOf(message);

      if (index === -1) {
        return messages;
      }

      return messages.filter((_, messageIndex) => messageIndex !== index);
    });

    const remainingMessages = this.activeMessages();

    this.message.set(
      remainingMessages.at(-1) ?? ApiLoadingMessage.Loading,
    );
  }
}
