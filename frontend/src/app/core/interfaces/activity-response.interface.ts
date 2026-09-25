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
  data_model: string;
  time: string;
  icon: string;
  accent: string;
}
