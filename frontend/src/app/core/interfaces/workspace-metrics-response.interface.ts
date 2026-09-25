/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: workspace-metrics-response.interface.ts
 * Purpose: API response contract for Workspace metrics.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface WorkspaceMetricsResponse {
  total_data_models: number;
  total_entities: number;
  generated_datasets: number;
  total_records: number;
}
