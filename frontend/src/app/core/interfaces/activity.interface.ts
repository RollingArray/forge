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
  dataModel: string;
  time: string;
  icon: string;
  accent: string;
}
