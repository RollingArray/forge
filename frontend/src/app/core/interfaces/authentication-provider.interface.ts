/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: authentication-provider.interface.ts
 * Purpose: Authentication provider abstraction for FORGE.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { AuthSession } from './auth-session.interface';
import { LoginRequest } from './login-request.interface';

export interface AuthenticationProvider {
  login(request: LoginRequest): Promise<AuthSession>;
  logout(): Promise<void>;
  getSession(): AuthSession | null;
}
