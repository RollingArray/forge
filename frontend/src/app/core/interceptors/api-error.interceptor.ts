/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: api-error.interceptor.ts
 * Purpose: Converts API failures into application-wide notifications.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  HttpErrorResponse,
  HttpInterceptorFn,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { NotificationService } from '../services/notification.service';

interface ApiErrorBody {
  detail?: string;
  message?: string;
}

export const apiErrorInterceptor: HttpInterceptorFn = (request, next) => {
  const notificationService = inject(NotificationService);

  return next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status !== 401) {
        notificationService.error(
          getErrorTitle(error.status),
          getErrorMessage(error),
          error.status || null,
        );
      }

      return throwError(() => error);
    }),
  );
};

function getErrorTitle(status: number): string {
  switch (status) {
    case 400:
      return 'Request could not be completed';

    case 403:
      return 'Access denied';

    case 404:
      return 'Resource not found';

    case 409:
      return 'Request conflicts with the current model';

    case 422:
      return 'Invalid request';

    default:
      return status >= 500
        ? 'FORGE could not complete the request'
        : 'Request could not be completed';
  }
}

function getErrorMessage(error: HttpErrorResponse): string {
  const body =
    error.error as ApiErrorBody | string | null | undefined;

  if (typeof body === 'string' && body.trim()) {
    return body;
  }

  if (body && typeof body === 'object') {
    if (typeof body.detail === 'string' && body.detail.trim()) {
      return body.detail;
    }

    if (typeof body.message === 'string' && body.message.trim()) {
      return body.message;
    }
  }

  return error.status >= 500
    ? 'An unexpected server error occurred. Please try again.'
    : 'The request could not be completed. Please review the model and try again.';
}
