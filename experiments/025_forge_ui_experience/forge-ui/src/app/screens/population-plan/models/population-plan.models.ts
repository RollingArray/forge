export type PopulationMode =
  | 'EXPLICIT'
  | 'AUTO';

export type PopulationStatus =
  | 'FEASIBLE'
  | 'WARNING'
  | 'INFEASIBLE';

export interface PopulationEntry {
  mode: PopulationMode;
  requested: number | null;
  minimumFeasible: number | null;
  resolved: number | null;
  status: PopulationStatus;
  reason: string;
  recommendation: string | null;
}

export interface PopulationRelationshipRequirement {
  entity: string;
  minimum: number;
  relationship: string;
  reason: string;
}

export interface PopulationCapacityRequirement {
  entity: string;
  minimum: number;
  relationship: string;
  reason: string;
}

export interface PopulationCapacityLimit {
  entity: string;
  maximum: number;
  relationship: string;
  reason: string;
}

export interface PopulationPlan {
  populations: Record<string, PopulationEntry>;
  minimums: Record<string, number>;
  maximums: Record<string, number>;
  relationshipRequirements: PopulationRelationshipRequirement[];
  capacityRequirements: PopulationCapacityRequirement[];
  capacityLimits: PopulationCapacityLimit[];
}


export interface PopulationTableRow {
  readonly entity: string;
  readonly mode: PopulationMode;
  readonly requested: number | null;
  readonly minimumFeasible: number | null;
  readonly maximumFeasible: number | null;
  readonly resolved: number | null;
  readonly status: PopulationStatus;
  readonly reason: string;
  readonly recommendation: string | null;
}


export interface PopulationHierarchyNode {
  readonly entity: string;
  readonly level: number;
  readonly resolved: number;
  readonly relationshipCount: number;
}

export interface PopulationCardinalityItem {
  readonly source: string;
  readonly target: string;
  readonly type: string;
  readonly sourceCardinality: string;
  readonly targetCardinality: string;
  readonly sourceParticipation: string;
  readonly targetParticipation: string;
  readonly sourceFields: readonly string[];
  readonly targetFields: readonly string[];
}


export type PopulationInsightType =
  | 'info'
  | 'constraint'
  | 'capacity'
  | 'population';

export interface PopulationInsight {
  readonly type: PopulationInsightType;
  readonly title: string;
  readonly message: string;
  readonly entity?: string;
}
