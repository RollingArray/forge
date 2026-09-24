/**
 * File: api-loading.interceptor.ts
 * Purpose: Track active FORGE API requests for global loading feedback.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize } from 'rxjs';

import { ApiLoadingService } from '../services/api-loading.service';

export const apiLoadingInterceptor: HttpInterceptorFn = (request, next) => {
  const apiLoadingService = inject(ApiLoadingService);

  const isLoginRequest =
    request.url.includes('/api/v1/auth/login');

  if (!isLoginRequest) {
    apiLoadingService.start();
  }

  return next(request).pipe(
    finalize(() => {
      if (!isLoginRequest) {
        apiLoadingService.stop();
      }
    }),
  );
};
