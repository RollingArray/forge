/**
 * File: resource.registry.ts
 * Purpose: Central definitions and route resolution for supported FORGE resources.
 */

import { ResourceDefinition } from '../interfaces/resource-definition.interface';
import { ResourceReference } from '../interfaces/resource-reference.interface';
import { ResourceType } from '../types/resource-type.type';

function buildModelRoute(
  reference: ResourceReference,
  section: string,
): string[] | null {
  if (!reference.dataModelId.trim() || reference.jobId) {
    return null;
  }

  return ['/workspace', reference.dataModelId, section];
}

function buildDataModelRoute(
  reference: ResourceReference,
  section: string,
): string[] | null {
  if (!reference.dataModelId.trim() || reference.jobId) {
    return null;
  }

  return ['/workspace', reference.dataModelId, 'data-model', section];
}

function buildJobRoute(
  reference: ResourceReference,
  section: string,
  suffix?: string,
): string[] | null {
  if (!reference.dataModelId.trim() || !reference.jobId?.trim()) {
    return null;
  }

  return [
    '/workspace',
    reference.dataModelId,
    'data-model',
    section,
    reference.jobId,
    ...(suffix ? [suffix] : []),
  ];
}

export const RESOURCE_DEFINITIONS: Readonly<
  Record<ResourceType, ResourceDefinition>
> = {
  model_studio: {
    type: 'model_studio',
    label: 'Model Studio',
    icon: 'account_tree',
    requiresJobId: false,
    buildRoute: (reference) => buildModelRoute(reference, 'model-studio'),
  },
  model_validation: {
    type: 'model_validation',
    label: 'Model Validation',
    icon: 'fact_check',
    requiresJobId: false,
    buildRoute: (reference) => buildModelRoute(reference, 'model-validation'),
  },
  population_plan: {
    type: 'population_plan',
    label: 'Population Plan',
    icon: 'groups',
    requiresJobId: false,
    buildRoute: (reference) => buildDataModelRoute(reference, 'population'),
  },
  generation: {
    type: 'generation',
    label: 'Generate',
    icon: 'play_circle',
    requiresJobId: false,
    buildRoute: (reference) => buildDataModelRoute(reference, 'generate'),
  },
  generation_execution: {
    type: 'generation_execution',
    label: 'Generation Execution',
    icon: 'terminal',
    requiresJobId: true,
    buildRoute: (reference) => buildJobRoute(reference, 'generate'),
  },
  generation_results: {
    type: 'generation_results',
    label: 'Generation Results',
    icon: 'analytics',
    requiresJobId: true,
    buildRoute: (reference) => buildJobRoute(reference, 'results'),
  },
  generated_table: {
    type: 'generated_table',
    label: 'Generated Table',
    icon: 'table_chart',
    requiresJobId: true,
    buildRoute: (reference) => {
      if (!reference.entityName?.trim()) {
        return null;
      }

      const baseRoute = buildJobRoute(reference, 'results');
      return baseRoute
        ? [...baseRoute, 'data', reference.entityName]
        : null;
    },
  },
  validation_analysis: {
    type: 'validation_analysis',
    label: 'Validation Analysis',
    icon: 'fact_check',
    requiresJobId: true,
    buildRoute: (reference) =>
      buildJobRoute(reference, 'results', 'validation-analysis'),
  },
  quality_analysis: {
    type: 'quality_analysis',
    label: 'Quality Analysis',
    icon: 'query_stats',
    requiresJobId: true,
    buildRoute: (reference) =>
      buildJobRoute(reference, 'results', 'quality-analysis'),
  },
};

export function resolveResourceReferenceFromUrl(
  url: string,
): ResourceReference | null {
  const segments = url.split('?')[0].split('#')[0].split('/').filter(Boolean);

  if (
    segments[0] !== 'workspace' ||
    !segments[1] ||
    segments[1] === 'favorites' ||
    segments[1] === 'ui-kit-design-system'
  ) {
    return null;
  }

  const dataModelId = segments[1];
  let resourceType: ResourceType | null = null;
  let jobId: string | undefined;

  if (segments[2] === 'model-studio' && segments.length === 3) {
    resourceType = 'model_studio';
  } else if (segments[2] === 'model-validation' && segments.length === 3) {
    resourceType = 'model_validation';
  } else if (
    segments[2] === 'data-model' &&
    segments[3] === 'population' &&
    segments.length === 4
  ) {
    resourceType = 'population_plan';
  } else if (
    segments[2] === 'data-model' &&
    segments[3] === 'generate' &&
    segments.length === 4
  ) {
    resourceType = 'generation';
  } else if (
    segments[2] === 'data-model' &&
    segments[3] === 'generate' &&
    segments[4] &&
    segments.length === 5
  ) {
    resourceType = 'generation_execution';
    jobId = segments[4];
  } else if (
    segments[2] === 'data-model' &&
    segments[3] === 'results' &&
    segments[4] &&
    segments.length === 5
  ) {
    resourceType = 'generation_results';
    jobId = segments[4];
  } else if (
    segments[2] === 'data-model' &&
    segments[3] === 'results' &&
    segments[4] &&
    segments[5] === 'data' &&
    segments[6] &&
    segments.length === 7
  ) {
    resourceType = 'generated_table';
    jobId = segments[4];
  } else if (
    segments[2] === 'data-model' &&
    segments[3] === 'results' &&
    segments[4] &&
    segments[5] === 'validation-analysis' &&
    segments.length === 6
  ) {
    resourceType = 'validation_analysis';
    jobId = segments[4];
  } else if (
    segments[2] === 'data-model' &&
    segments[3] === 'results' &&
    segments[4] &&
    segments[5] === 'quality-analysis' &&
    segments.length === 6
  ) {
    resourceType = 'quality_analysis';
    jobId = segments[4];
  }

  if (!resourceType) {
    return null;
  }

  const reference: ResourceReference = {
    resourceType,
    dataModelId,
    ...(jobId ? { jobId } : {}),
    ...(resourceType === 'generated_table' ? { entityName: segments[6] } : {}),
  };

  return RESOURCE_DEFINITIONS[resourceType].buildRoute(reference)
    ? reference
    : null;
}

export function resolveResourceRoute(
  reference: ResourceReference,
): string[] | null {
  const definition = RESOURCE_DEFINITIONS[reference.resourceType];

  if (!definition || !reference.dataModelId.trim()) {
    return null;
  }

  if (definition.requiresJobId !== Boolean(reference.jobId?.trim())) {
    return null;
  }

  return definition.buildRoute(reference);
}
