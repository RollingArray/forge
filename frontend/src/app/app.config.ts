/**
 * File: app.config.ts
 * Purpose: Application-wide Angular configuration and dependency injection.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import {
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import { provideRouter } from '@angular/router';

import { AUTHENTICATION_PROVIDER } from './core/interfaces/authentication-provider.token';
import { DevelopmentAuthenticationProviderService } from './core/services/development-authentication-provider.service';
import { authTokenInterceptor } from './core/interceptors/auth-token.interceptor';
import { apiLoadingInterceptor } from './core/interceptors/api-loading.interceptor';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(
      withInterceptors([
        authTokenInterceptor,
        apiLoadingInterceptor,
      ]),
    ),
    {
      provide: AUTHENTICATION_PROVIDER,
      useExisting: DevelopmentAuthenticationProviderService,
    },
  ],
};
