/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: ai-capability.interface.ts
 * Purpose: Defines the frontend contract for FORGE AI capability status.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface AICapability {
  available: boolean;
  provider: string;
  mode: string;
  model: string | null;
  message: string;
}
