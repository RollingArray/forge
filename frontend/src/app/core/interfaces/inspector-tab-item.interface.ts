/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: inspector-tab-item.interface.ts
 * Purpose: Defines the inspector navigation tab item contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import type { InspectorTab } from '../types/inspector-tab.type';

export interface InspectorTabItem {
  id: InspectorTab;
  label: string;
  shortLabel: string;
  icon: string;
  count: number;
}
