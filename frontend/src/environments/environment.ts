/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: environment.ts
 * Purpose: Production environment configuration for the FORGE frontend.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export const environment = {
  production: true,
  apiBaseUrl: 'http://127.0.0.1:8000/api/v1',
} as const;
