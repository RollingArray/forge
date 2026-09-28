/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: population.models.ts
 * Purpose: Population planning models used by the FORGE Population feature.
 *
 * ============================================================================
 */

export type PopulationMode = 'EXPLICIT' | 'AUTO';

export type PopulationScaling = 'FIXED' | 'SCALABLE';

export type PopulationStatus =
  | 'FEASIBLE'
  | 'INFEASIBLE'
  | 'AUTO'
  | 'UNRESOLVED';

export interface PopulationEntityPlan {
  mode: PopulationMode;
  scaling: PopulationScaling;
  requested: number | null;
  minimum_feasible: number | null;
  resolved: number | null;
  status: PopulationStatus;
  reason: string | null;
  recommendation: string | null;
}

export interface PopulationRequirement {
  entity: string;
  minimum: number;
  relationship: string;
  reason: string;
}

export interface CapacityRequirement {
  entity: string;
  minimum: number;
  relationship: string;
  reason: string;
}

export interface CapacityLimit {
  entity: string;
  maximum: number;
  relationship: string;
  reason: string;
}

export interface PopulationPlan {
  populations: Record<string, PopulationEntityPlan>;
  minimums: Record<string, number>;
  maximums: Record<string, number>;
  relationship_requirements: PopulationRequirement[];
  capacity_requirements: CapacityRequirement[];
  capacity_limits: CapacityLimit[];
}

export interface PopulationCandidatePlan extends PopulationPlan {
  target: number;
  driver: string;
  fixed_total: number;
  scalable_total: number;
  allocated_total: number;
  target_feasible: boolean;
  target_reason: string | null;
  feasible: boolean;
}
