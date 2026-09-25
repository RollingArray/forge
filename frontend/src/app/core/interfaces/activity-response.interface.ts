/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: activity-response.interface.ts
 * Purpose: API response contract for Workspace activity.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface ActivityResponse {
  action: string;
  description: string;
  data_model: string;
  actor: string;
  target: string | null;
  time: string;
  icon: string;
  accent: string;
}
