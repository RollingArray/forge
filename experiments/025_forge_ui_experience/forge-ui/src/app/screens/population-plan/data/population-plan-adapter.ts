import {
  PopulationCapacityLimit,
  PopulationCapacityRequirement,
  PopulationEntry,
  PopulationPlan,
  PopulationRelationshipRequirement,
} from '../models/population-plan.models';

interface RawPopulationEntry {
  mode?: string;
  requested?: number | null;
  minimum_feasible?: number | null;
  resolved?: number | null;
  status?: string;
  reason?: string;
  recommendation?: string | null;
}

interface RawRelationshipRequirement {
  entity: string;
  minimum: number;
  relationship: string;
  reason: string;
}

interface RawCapacityRequirement {
  entity: string;
  minimum: number;
  relationship: string;
  reason: string;
}

interface RawCapacityLimit {
  entity: string;
  maximum: number;
  relationship: string;
  reason: string;
}

interface RawPopulationPlan {
  populations: Record<string, RawPopulationEntry>;
  minimums?: Record<string, number>;
  maximums?: Record<string, number>;
  relationship_requirements?: RawRelationshipRequirement[];
  capacity_requirements?: RawCapacityRequirement[];
  capacity_limits?: RawCapacityLimit[];
}

function adaptPopulationEntry(
  entry: RawPopulationEntry,
): PopulationEntry {
  return {
    mode:
      entry.mode === 'AUTO'
        ? 'AUTO'
        : 'EXPLICIT',

    requested:
      entry.requested ?? null,

    minimumFeasible:
      entry.minimum_feasible ?? null,

    resolved:
      entry.resolved ?? null,

    status:
      entry.status === 'INFEASIBLE'
        ? 'INFEASIBLE'
        : entry.status === 'WARNING'
          ? 'WARNING'
          : 'FEASIBLE',

    reason:
      entry.reason ?? '',

    recommendation:
      entry.recommendation ?? null,
  };
}

function adaptRelationshipRequirement(
  requirement: RawRelationshipRequirement,
): PopulationRelationshipRequirement {
  return {
    entity: requirement.entity,
    minimum: requirement.minimum,
    relationship: requirement.relationship,
    reason: requirement.reason,
  };
}

function adaptCapacityRequirement(
  requirement: RawCapacityRequirement,
): PopulationCapacityRequirement {
  return {
    entity: requirement.entity,
    minimum: requirement.minimum,
    relationship: requirement.relationship,
    reason: requirement.reason,
  };
}

function adaptCapacityLimit(
  limit: RawCapacityLimit,
): PopulationCapacityLimit {
  return {
    entity: limit.entity,
    maximum: limit.maximum,
    relationship: limit.relationship,
    reason: limit.reason,
  };
}

export function adaptPopulationPlan(
  raw: RawPopulationPlan,
): PopulationPlan {
  const populations: Record<string, PopulationEntry> =
    Object.fromEntries(
      Object.entries(raw.populations ?? {}).map(
        ([entity, entry]) => [
          entity,
          adaptPopulationEntry(entry),
        ],
      ),
    );

  const relationshipRequirements =
    (raw.relationship_requirements ?? []).map(
      adaptRelationshipRequirement,
    );

  const capacityRequirements =
    (raw.capacity_requirements ?? []).map(
      adaptCapacityRequirement,
    );

  const capacityLimits =
    (raw.capacity_limits ?? []).map(
      adaptCapacityLimit,
    );

  return {
    populations,

    minimums:
      raw.minimums ?? {},

    maximums:
      raw.maximums ?? {},

    relationshipRequirements,

    capacityRequirements,

    capacityLimits,
  };
}
