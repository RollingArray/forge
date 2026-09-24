import { Injectable } from '@angular/core';

import {
  ValidationCategory,
  ValidationEntity,
  ValidationFinding,
  ValidationViewModel,
} from '../models/validate.models';

import {
  ValidationSpecification,
  ValidationSpecificationEntity,
  ValidationSpecificationField,
} from './validation-data.service';

@Injectable({
  providedIn: 'root',
})
export class SpecificationValidationService {
  validate(
    specification: ValidationSpecification,
  ): ValidationViewModel {
    const findings: ValidationFinding[] = [];
    let sequence = 0;

    const add = (
      severity: ValidationFinding['severity'],
      category: ValidationCategory,
      title: string,
      details: string,
      entity?: string,
      field?: string,
    ): void => {
      findings.push({
        id: `validation-${++sequence}`,
        severity,
        category,
        title,
        details,
        entity,
        field,
      });
    };

    const entities =
      specification.entities ?? [];

    const entityNames =
      new Set<string>();

    const duplicateEntityNames =
      new Set<string>();

    for (const entity of entities) {
      const name =
        entity.name?.trim();

      if (!name) {
        add(
          'error',
          'Entity',
          'Entity name is missing',
          'Every entity must have a non-empty name.',
        );

        continue;
      }

      if (entityNames.has(name)) {
        duplicateEntityNames.add(name);

        add(
          'error',
          'Entity',
          'Duplicate entity name',
          `Entity '${name}' is defined more than once.`,
          name,
        );
      }

      entityNames.add(name);
    }

    if (
      specification.version?.trim()
    ) {
      add(
        'passed',
        'Specification',
        'Specification version is defined',
        `Version ${specification.version}.`,
      );
    } else {
      add(
        'error',
        'Specification',
        'Specification version is missing',
        'A specification version is required.',
      );
    }

    if (
      specification.vocabulary_version?.trim()
    ) {
      add(
        'passed',
        'Specification',
        'Vocabulary version is defined',
        `Vocabulary version ${specification.vocabulary_version}.`,
      );
    } else {
      add(
        'error',
        'Specification',
        'Vocabulary version is missing',
        'A vocabulary version is required.',
      );
    }

    if (
      specification.model?.name?.trim()
    ) {
      add(
        'passed',
        'Model',
        'Model definition is valid',
        `Model '${specification.model.name}' is defined.`,
      );
    } else {
      add(
        'error',
        'Model',
        'Model name is missing',
        'The specification must identify the model.',
      );
    }

    const seed =
      specification.generation?.seed;

    if (
      typeof seed === 'number' &&
      Number.isInteger(seed)
    ) {
      add(
        'passed',
        'Generation',
        'Generation seed is valid',
        `Seed ${seed} is configured.`,
      );
    } else {
      add(
        'error',
        'Generation',
        'Generation seed is invalid',
        'Generation seed must be an integer.',
      );
    }

    const fieldsByEntity =
      new Map<
        string,
        Set<string>
      >();

    for (const entity of entities) {
      this.validateEntity(
        entity,
        entityNames,
        fieldsByEntity,
        add,
      );
    }

    const relationships =
      specification.relationships ?? [];

    for (
      const relationship of relationships
    ) {
      const source =
        relationship.source?.trim();

      const target =
        relationship.target?.trim();

      const validType = [
        'ONE_TO_ONE',
        'ONE_TO_MANY',
        'MANY_TO_ONE',
        'MANY_TO_MANY',
      ].includes(
        relationship.type ?? '',
      );

      const validParticipation = [
        'REQUIRED',
        'OPTIONAL',
      ];

      const valid =
        !!source &&
        !!target &&
        entityNames.has(source) &&
        entityNames.has(target) &&
        validType &&
        validParticipation.includes(
          relationship.source_participation ??
            '',
        ) &&
        validParticipation.includes(
          relationship.target_participation ??
            '',
        );

      if (valid) {
        add(
          'passed',
          'Relationship',
          'Relationship is valid',
          `${source} → ${target} (${relationship.type}).`,
          source,
        );
      } else {
        add(
          'error',
          'Relationship',
          'Invalid relationship definition',
          `${source || 'Unknown'} → ${target || 'Unknown'} has invalid entities, type, or participation.`,
          source,
        );
      }
    }

    const foreignKeys =
      specification.foreign_keys ?? [];

    const foreignKeyNames =
      new Set<string>();

    for (
      const foreignKey of foreignKeys
    ) {
      const name =
        foreignKey.name?.trim() ||
        `Foreign key ${sequence + 1}`;

      const sourceEntity =
        foreignKey.source?.entity?.trim();

      const targetEntity =
        foreignKey.target?.entity?.trim();

      const sourceFields =
        foreignKey.source?.fields ?? [];

      const targetFields =
        foreignKey.target?.fields ?? [];

      const sourceFieldSet =
        fieldsByEntity.get(
          sourceEntity ?? '',
        );

      const targetFieldSet =
        fieldsByEntity.get(
          targetEntity ?? '',
        );

      const fieldsValid =
        !!sourceFieldSet &&
        !!targetFieldSet &&
        sourceFields.length > 0 &&
        targetFields.length > 0 &&
        sourceFields.length ===
          targetFields.length &&
        sourceFields.every(field =>
          sourceFieldSet.has(field),
        ) &&
        targetFields.every(field =>
          targetFieldSet.has(field),
        );

      const duplicate =
        foreignKeyNames.has(name);

      foreignKeyNames.add(name);

      if (fieldsValid && !duplicate) {
        add(
          'passed',
          'Foreign Key',
          'Foreign key is valid',
          `${sourceEntity}.${sourceFields.join(', ')} references ${targetEntity}.${targetFields.join(', ')}.`,
          sourceEntity,
        );
      } else {
        add(
          'error',
          'Foreign Key',
          duplicate
            ? 'Duplicate foreign key name'
            : 'Invalid foreign key definition',
          duplicate
            ? `Foreign key '${name}' is defined more than once.`
            : `${sourceEntity || 'Unknown'} → ${targetEntity || 'Unknown'} has invalid entity or field mappings.`,
          sourceEntity,
        );
      }
    }

    const constraints =
      specification.constraints ?? [];

    for (
      const constraint of constraints
    ) {
      const entity =
        constraint.entity?.trim();

      const field =
        constraint.field?.trim();

      const fieldSet =
        fieldsByEntity.get(entity ?? '');

      const valid =
        !!entity &&
        !!field &&
        entityNames.has(entity) &&
        !!fieldSet?.has(field) &&
        !!constraint.operator;

      if (valid) {
        add(
          'passed',
          'Constraint',
          'Constraint is valid',
          `${entity}.${field} ${constraint.operator} ${constraint.value ?? ''}`.trim(),
          entity,
          field,
        );
      } else {
        add(
          'error',
          'Constraint',
          'Invalid constraint',
          `${entity || 'Unknown'}.${field || 'Unknown'} references a missing entity or field.`,
          entity,
          field,
        );
      }
    }

    if (
      entities.length > 0 &&
      duplicateEntityNames.size === 0
    ) {
      add(
        'passed',
        'Specification',
        'Entity definitions are unique',
        `${entities.length} entities are defined.`,
      );
    }

    const entityModels =
      this.buildEntityResults(
        entities,
        findings,
      );

    const errors =
      findings.filter(
        finding =>
          finding.severity === 'error',
      ).length;

    const warnings =
      findings.filter(
        finding =>
          finding.severity === 'warning',
      ).length;

    const passed =
      findings.filter(
        finding =>
          finding.severity === 'passed',
      ).length;

    const totalChecks =
      errors +
      warnings +
      passed;

    return {
      modelName:
        specification.model?.name ??
        'Untitled Model',

      specificationVersion:
        specification.version ??
        'Unknown',

      vocabularyVersion:
        specification.vocabulary_version ??
        'Unknown',

      errors,
      warnings,
      passed,
      totalChecks,

      entitiesValidated:
        entities.length,

      canContinue:
        errors === 0,

      findings,

      entities:
        entityModels,
    };
  }

  private validateEntity(
    entity: ValidationSpecificationEntity,
    entityNames: ReadonlySet<string>,
    fieldsByEntity: Map<string, Set<string>>,
    add: (
      severity: ValidationFinding['severity'],
      category: ValidationCategory,
      title: string,
      details: string,
      entity?: string,
      field?: string,
    ) => void,
  ): void {
    const name =
      entity.name?.trim();

    if (!name) {
      return;
    }

    const fields =
      entity.fields ?? [];

    const fieldNames =
      new Set<string>();

    let valid = true;

    for (
      const field of fields
    ) {
      const fieldName =
        field.name?.trim();

      if (!fieldName) {
        valid = false;

        add(
          'error',
          'Entity',
          'Field name is missing',
          `Entity '${name}' contains a field without a name.`,
          name,
        );

        continue;
      }

      if (
        fieldNames.has(fieldName)
      ) {
        valid = false;

        add(
          'error',
          'Entity',
          'Duplicate field name',
          `Field '${fieldName}' is defined more than once.`,
          name,
          fieldName,
        );
      }

      fieldNames.add(fieldName);

      if (!field.type?.trim()) {
        valid = false;

        add(
          'error',
          'Entity',
          'Field type is missing',
          `Field '${fieldName}' does not define a type.`,
          name,
          fieldName,
        );
      }
    }

    fieldsByEntity.set(
      name,
      fieldNames,
    );

    const identityFields =
      entity.identity?.fields ?? [];

    if (
      identityFields.length === 0
    ) {
      valid = false;

      add(
        'error',
        'Entity',
        'Identity definition is missing',
        `Entity '${name}' does not define an identity field.`,
        name,
      );
    } else {
      for (
        const identityField of identityFields
      ) {
        if (
          !fieldNames.has(
            identityField,
          )
        ) {
          valid = false;

          add(
            'error',
            'Entity',
            'Identity field is missing',
            `Identity field '${identityField}' is not defined on '${name}'.`,
            name,
            identityField,
          );
        }
      }
    }

    const population =
      entity.population?.count;

    if (
      typeof population === 'number' &&
      Number.isInteger(population) &&
      population >= 0
    ) {
      // valid
    } else {
      valid = false;

      add(
        'error',
        'Entity',
        'Population count is invalid',
        `Entity '${name}' must define a non-negative integer population count.`,
        name,
      );
    }

    if (valid) {
      add(
        'passed',
        'Entity',
        'Entity definition is valid',
        `${fields.length} fields and ${identityFields.length} identity field${identityFields.length === 1 ? '' : 's'} are defined.`,
        name,
      );
    }
  }

  private buildEntityResults(
    entities: readonly ValidationSpecificationEntity[],
    findings: readonly ValidationFinding[],
  ): ValidationEntity[] {
    return entities
      .map(entity => {
        const name =
          entity.name ?? 'Unnamed Entity';

        const entityFindings =
          findings.filter(
            finding =>
              finding.entity === name,
          );

        const errors =
          entityFindings.filter(
            finding =>
              finding.severity === 'error',
          ).length;

        const warnings =
          entityFindings.filter(
            finding =>
              finding.severity === 'warning',
          ).length;

        return {
          name,
          status:
            errors > 0
              ? 'error'
              : warnings > 0
                ? 'warning'
                : 'valid',
          checks:
            entityFindings.length,
          errors,
          warnings,
        };
      });
  }
}
