export type GenerationStage =
  | 'load-specification'
  | 'initialize-plan'
  | 'resolve-dependencies'
  | 'generate-data'
  | 'validate'
  | 'complete';

export interface GenerationEntityPlan {
  readonly entity: string;
  readonly targetRows: number;
  readonly dependencies: readonly string[];
}
