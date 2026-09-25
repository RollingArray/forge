/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: workspace-data.interface.ts
 * Purpose: Aggregated Workspace data returned by WorkspaceService.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { Activity } from './activity.interface';
import { DataModel } from './data-model.interface';
import { Metric } from './metric.interface';
import { Template } from './template.interface';

export interface WorkspaceData {
  metrics: Metric[];
  dataModels: DataModel[];
  templates: Template[];
  activities: Activity[];
}
