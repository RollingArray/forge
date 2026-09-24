/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: authentication-provider.token.ts
 * Purpose: Angular dependency injection token for the authentication provider.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { InjectionToken } from '@angular/core';

import { AuthenticationProvider } from './authentication-provider.interface';

export const AUTHENTICATION_PROVIDER =
  new InjectionToken<AuthenticationProvider>(
    'FORGE_AUTHENTICATION_PROVIDER',
  );
