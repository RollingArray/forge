import { MODEL_NODE_HEIGHT, MODEL_NODE_WIDTH } from './model-geometry';

import { layoutModel } from './model-layout';

import {
  CanvasEntity,
  EntityAccent,
  ForgeForeignKey,
  ForgeSpecification,
  ForgeSpecificationEntity,
  ForgeSpecificationField,
  ModelConstraint,
  ModelEntity,
  ModelField,
  ModelRelationship,
  ModelStudioData,
} from '../models/model-studio.models';

const ACCENTS: EntityAccent[] = [
  'blue',
  'green',
  'amber',
  'pink',
  'purple',
];

function buildForeignKeyFieldMap(
  foreignKeys: readonly ForgeForeignKey[],
): Map<string, Set<string>> {
  const result = new Map<string, Set<string>>();

  for (const foreignKey of foreignKeys) {
    const entityName = foreignKey.source.entity;

    if (!result.has(entityName)) {
      result.set(entityName, new Set<string>());
    }

    for (const field of foreignKey.source.fields) {
      result.get(entityName)!.add(field);
    }
  }

  return result;
}

function buildField(
  field: ForgeSpecificationField,
  identityFields: readonly string[],
  foreignKeyFields: ReadonlySet<string>,
): ModelField {
  const isPrimaryKey = identityFields.includes(field.name);

  return {
    name: field.name,
    type: field.type,
    description: field.description ?? '',
    generation: field.generation
      ? {
          strategy: field.generation.strategy,
          distribution: field.generation.distribution,
          parameters: field.generation.parameters,
        }
      : undefined,
    identityStrategy: isPrimaryKey
      ? field.identity?.strategy
      : undefined,
    required: isPrimaryKey,
    primaryKey: isPrimaryKey,
    foreignKey: foreignKeyFields.has(field.name),
  };
}

function buildEntity(
  entity: ForgeSpecificationEntity,
  index: number,
  foreignKeyFields: ReadonlyMap<string, ReadonlySet<string>>,
): CanvasEntity {
  const identityFields = entity.identity?.fields ?? [];
  const entityForeignKeyFields =
    foreignKeyFields.get(entity.name) ?? new Set<string>();

  const fields = entity.fields.map(field =>
    buildField(
      field,
      identityFields,
      entityForeignKeyFields,
    ),
  );

  return {
    name: entity.name,
    description: entity.description ?? '',
    accent: entity.color ?? ACCENTS[index % ACCENTS.length],
    fields,
    populationCount: entity.population?.count ?? 0,
    identityFields,
    primaryKey: {
      fields: identityFields,
      composite: identityFields.length > 1,
    },
    x: 0,
    y: 0,
    width: MODEL_NODE_WIDTH,
    height: MODEL_NODE_HEIGHT,
    keyCount: fields.filter(
      field =>
        field.primaryKey ||
        field.foreignKey,
    ).length,
    relationshipCount: 0,
    constraintCount: 0,
  };
}

function endpointEntityName(endpoint: string): string {
  return endpoint.split('.')[0];
}

function cardinalityForParticipation(
  type: string,
  side: 'source' | 'target',
): string {
  switch (type) {
    case 'ONE_TO_ONE':
      return '1';

    case 'ONE_TO_MANY':
      return side === 'source'
        ? '1'
        : 'N';

    case 'MANY_TO_ONE':
      return side === 'source'
        ? 'N'
        : '1';

    case 'MANY_TO_MANY':
      return 'N';

    default:
      return '?';
  }
}

function buildRelationships(
  specification: ForgeSpecification,
): ModelRelationship[] {
  const foreignKeys =
    specification.foreign_keys ?? [];

  return specification.relationships.map(
    relationship => {
      const source =
        endpointEntityName(
          relationship.source,
        );

      const target =
        endpointEntityName(
          relationship.target,
        );

      /*
       * A relationship describes the logical relationship
       * direction, while the FK may physically exist in
       * either direction.
       *
       * Resolve both orientations so the UI always gets
       * the correct source/target field mapping.
       */
      const matchingForeignKeys =
        foreignKeys.filter(
          foreignKey =>
            (
              foreignKey.source.entity === source &&
              foreignKey.target.entity === target
            ) ||
            (
              foreignKey.source.entity === target &&
              foreignKey.target.entity === source
            ),
        );

      const sourceFields: string[] = [];
      const targetFields: string[] = [];

      for (
        const foreignKey of matchingForeignKeys
      ) {
        if (
          foreignKey.source.entity === source &&
          foreignKey.target.entity === target
        ) {
          sourceFields.push(
            ...foreignKey.source.fields,
          );

          targetFields.push(
            ...foreignKey.target.fields,
          );
        } else {
          /*
           * FK is physically reversed relative to the
           * logical relationship.
           */
          sourceFields.push(
            ...foreignKey.target.fields,
          );

          targetFields.push(
            ...foreignKey.source.fields,
          );
        }
      }

      return {
        source,
        target,
        sourceCardinality:
          cardinalityForParticipation(
            relationship.type,
            'source',
          ),
        targetCardinality:
          cardinalityForParticipation(
            relationship.type,
            'target',
          ),
        sourceParticipation:
          relationship.source_participation ??
          'OPTIONAL',
        targetParticipation:
          relationship.target_participation ??
          'OPTIONAL',
        type: relationship.type,
        sourceFields: [
          ...new Set(sourceFields),
        ],
        targetFields: [
          ...new Set(targetFields),
        ],
      };
    },
  );
}


function buildConstraints(
  specification: ForgeSpecification,
): ModelConstraint[] {
  return (specification.constraints ?? []).map(
    (constraint, index) => ({
      id: `spec-${index + 1}`,
      entity: constraint.entity,
      field: constraint.field,
      operator: constraint.operator,
      value: constraint.value,
      source: 'specification',
    }),
  );
}

export function adaptSpecification(
  specification: ForgeSpecification,
): ModelStudioData {
  const foreignKeyFields =
    buildForeignKeyFieldMap(specification.foreign_keys ?? []);

  const baseEntities = specification.entities.map(
    (entity, index) =>
      buildEntity(entity, index, foreignKeyFields),
  );

  const relationships =
    buildRelationships(specification);

  const constraints =
    buildConstraints(specification);

  const enrichedEntities =
    baseEntities.map(entity => ({
      ...entity,

      relationshipCount:
        relationships.filter(
          relationship =>
            relationship.source === entity.name ||
            relationship.target === entity.name,
        ).length,

      constraintCount:
        constraints.filter(
          constraint =>
            constraint.entity === entity.name,
        ).length,
    }));

  const entities =
    layoutModel(
      enrichedEntities,
      relationships,
    );

  return {
    entities,
    relationships,
    constraints,
  };
}
