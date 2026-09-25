/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: metric.interface.ts
 * Purpose: Defines the frontend contract for a Workspace metric.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface Metric {
  label: string;
  value: string;
  icon: string;
  accent: string;
  supportingText: string;
  supportingType: 'positive' | 'subtle' | 'progress';
}
