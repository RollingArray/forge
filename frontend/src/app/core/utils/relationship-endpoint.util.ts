import { ForgeRelationshipEndpointValue } from '../types/forge-relationship-endpoint-value.type';
import { NormalizedRelationshipEndpoint } from '../interfaces/normalized-relationship-endpoint.interface';

export function normalizeRelationshipEndpoint(
  endpoint: ForgeRelationshipEndpointValue,
): NormalizedRelationshipEndpoint {
  if (typeof endpoint !== 'string') {
    return {
      entity: endpoint.entity,
      fields: [...endpoint.fields],
    };
  }

  const separator = endpoint.indexOf('.');

  if (separator < 0) {
    return {
      entity: endpoint,
      fields: [],
    };
  }

  return {
    entity: endpoint.slice(0, separator),
    fields: endpoint.slice(separator + 1).split(',').filter(Boolean),
  };
}
