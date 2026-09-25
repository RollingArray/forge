/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: auth-token.interceptor.ts
 * Purpose: Adds the authenticated bearer token and handles unauthorized
 *          API responses.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from '../services/auth.service';

let logoutInProgress = false;

export const authTokenInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const session = authService.getSession();

  const authenticatedRequest = session?.accessToken
    ? request.clone({
        setHeaders: {
          Authorization: `${session.tokenType} ${session.accessToken}`,
        },
      })
    : request;

  return next(authenticatedRequest).pipe(
    catchError((error) => {
      const isUnauthorized = error.status === 401;
      const isLoginRequest = request.url.includes('/api/v1/auth/login');

      if (
        isUnauthorized &&
        !isLoginRequest &&
        !logoutInProgress
      ) {
        logoutInProgress = true;

        void authService
          .logout()
          .catch(() => {
            // Local session cleanup is guaranteed by AuthService.logout().
          })
          .finally(() => {
            void router.navigate(['/login']).finally(() => {
              logoutInProgress = false;
            });
          });
      }

      return throwError(() => error);
    }),
  );
};
