import {
  ForgeConstraint,
  ForgeForeignKey,
  ForgeSpecification,
  ForgeSpecificationEntity,
  ForgeSpecificationField,
} from '../../../core/interfaces/forge-specification.interface';

export type EntityAccent =
  | 'blue'
  | 'green'
  | 'orange'
  | 'pink'
  | 'purple'
  | 'teal'
  | 'amber'
  | 'cyan'
  | 'indigo'
  | 'rose';

export interface ModelFieldGeneration {
  strategy?: string;
  distribution?: string;
  parameters?: Record<string, unknown>;
}

export interface ModelField {
  name: string;
  type: string;
  description: string;
  generation?: ModelFieldGeneration;
  identityStrategy?: string;
  required?: boolean;
  primaryKey?: boolean;
  foreignKey?: boolean;
}

export interface ModelKey {
  fields: string[];
  composite: boolean;
}

export interface ModelEntity {
  name: string;
  description: string;
  accent: EntityAccent;
  fields: ModelField[];
  populationCount: number;
  identityFields: string[];
  primaryKey: ModelKey;
}

export interface CanvasEntity extends ModelEntity {
  x: number;
  y: number;
  width: number;
  height: number;
  keyCount: number;
  relationshipCount: number;
  constraintCount: number;
}

export interface ModelRelationship {
  source: string;
  target: string;
  sourceCardinality: string;
  targetCardinality: string;
  sourceParticipation: string;
  targetParticipation: string;
  type: string;
  sourceFields: string[];
  targetFields: string[];
}

export interface ModelConstraint {
  id: string;
  entity: string;
  field: string;
  operator: string;
  value: string | number | boolean;
  source: 'specification' | 'user';
}

export interface ModelStudioData {
  entities: CanvasEntity[];
  relationships: ModelRelationship[];
  constraints: ModelConstraint[];
}
