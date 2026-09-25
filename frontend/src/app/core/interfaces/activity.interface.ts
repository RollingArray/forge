/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: activity.interface.ts
 * Purpose: Defines the frontend contract for Workspace activity.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface Activity {
  action: string;
  description: string;
  dataModel: string;
  actor: string;
  target: string | null;
  time: string;
  icon: string;
  accent: string;
}
