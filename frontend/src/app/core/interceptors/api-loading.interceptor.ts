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

import { ApiLoadingMessage } from '../enums/api-loading-message.enum';
import { API_LOADING_MESSAGE } from '../tokens/api-loading-message.token';
import { API_LOADING_SKIP } from '../tokens/api-loading-skip.token';
import { ApiLoadingService } from '../services/api-loading.service';

export const apiLoadingInterceptor: HttpInterceptorFn = (request, next) => {
  const apiLoadingService = inject(ApiLoadingService);

  const isLoginRequest = request.url.includes('/api/v1/auth/login');
  const skipGlobalLoading = request.context.get(API_LOADING_SKIP);

  if (isLoginRequest || skipGlobalLoading) {
    return next(request);
  }

  const loadingMessage =
    request.context.get(API_LOADING_MESSAGE) ??
    ApiLoadingMessage.Loading;

  apiLoadingService.start(loadingMessage);

  return next(request).pipe(
    finalize(() => {
      apiLoadingService.stop(loadingMessage);
    }),
  );
};
