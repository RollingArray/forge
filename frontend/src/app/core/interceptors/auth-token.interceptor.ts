/**
 * File: auth-token.interceptor.ts
 * Purpose: Attach the FORGE access token to authenticated API requests.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { AuthService } from '../services/auth.service';

export const authTokenInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const session = authService.getSession();

  if (!session?.accessToken) {
    return next(request);
  }

  const authenticatedRequest = request.clone({
    setHeaders: {
      Authorization: `${session.tokenType} ${session.accessToken}`,
    },
  });

  return next(authenticatedRequest);
};
