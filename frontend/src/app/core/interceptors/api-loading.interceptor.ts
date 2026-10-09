/**
 * File: api-loading.interceptor.ts
 * Purpose: Tracks HTTP request loading state and loading messages.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize } from 'rxjs';

import { API_LOADING_MESSAGE } from '../tokens/api-loading-message.token';
import { API_LOADING_SKIP } from '../tokens/api-loading-skip.token';
import { ApiLoadingService } from '../services/api-loading.service';

export const apiLoadingInterceptor: HttpInterceptorFn = (request, next) => {
  const apiLoadingService = inject(ApiLoadingService);

  const isPublicAuthRequest =
    request.url.includes('/api/v1/auth/login') ||
    request.url.includes('/api/v1/auth/magic-link');
  const skipGlobalLoading = request.context.get(API_LOADING_SKIP);

  if (isPublicAuthRequest || skipGlobalLoading) {
    return next(request);
  }

  const loadingMessage = request.context.get(API_LOADING_MESSAGE);

  if (!loadingMessage) {
    throw new Error(
      `Missing API loading message for request: ${request.method} ${request.url}`,
    );
  }

  apiLoadingService.start(loadingMessage);

  return next(request).pipe(
    finalize(() => {
      apiLoadingService.stop(loadingMessage);
    }),
  );
};
