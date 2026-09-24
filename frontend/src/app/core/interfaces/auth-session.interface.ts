/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: auth-session.interface.ts
 * Purpose: Authenticated FORGE session contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { AuthUser } from './auth-user.interface';

export interface AuthSession {
  accessToken: string;
  tokenType: 'Bearer';
  user: AuthUser;
}
