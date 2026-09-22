export type StudioStep =
  | 'model'
  | 'validate'
  | 'population'
  | 'generate'
  | 'results';

export interface StudioStepItem {
  readonly id: StudioStep;
  readonly number: number;
  readonly label: string;
}

export interface StudioAction {
  label: string;
  icon: string;
  action: string;
}

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
  nullable?: boolean;
  required?: boolean;
  primaryKey?: boolean;
  foreignKey?: boolean;
}

export interface ModelEntity {
  name: string;
  description: string;
  accent: EntityAccent;
  isNew?: boolean;
  fields: ModelField[];

  populationCount: number;
  identityFields: string[];
  primaryKey: ModelKey;
}

export interface ModelKey {
  fields: string[];
  composite: boolean;
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

export interface ForgeSpecification {
  entities: ForgeSpecificationEntity[];
  relationships: ForgeSpecificationRelationship[];
  foreign_keys: ForgeForeignKey[];
  constraints: ForgeConstraint[];
  dependencies: unknown[];
  statistical_behavior: unknown[];
  scenarios: unknown[];
}

export interface ForgeSpecificationEntity {
  name: string;
  description?: string;
  color?: EntityAccent;
  population?: {
    count?: number;
  };
  fields: ForgeSpecificationField[];
  identity?: {
    fields?: string[];
  };
}

export interface ForgeSpecificationField {
  name: string;
  type: string;
  description?: string;
  generation?: {
    strategy?: string;
    distribution?: string;
    parameters?: Record<string, unknown>;
  };
  identity?: {
    strategy?: string;
  };
}

export interface ForgeSpecificationRelationship {
  source: string;
  target: string;
  type: string;
  source_participation?: string;
  target_participation?: string;
}

export interface ForgeForeignKey {
  name: string;
  source: {
    entity: string;
    fields: string[];
  };
  target: {
    entity: string;
    fields: string[];
  };
}

export interface ForgeConstraint {
  entity: string;
  field: string;
  operator: string;
  value: string | number | boolean;
}

export interface ModelStudioData {
  entities: CanvasEntity[];
  relationships: ModelRelationship[];
  constraints: ModelConstraint[];
}
