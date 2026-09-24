import { Injectable } from '@angular/core';

export interface ValidationSpecification {
  version?: string;
  vocabulary_version?: string;

  model?: {
    name?: string;
    description?: string;
  };

  generation?: {
    seed?: number;
    scenario?: string;
  };

  entities?: ValidationSpecificationEntity[];
  relationships?: ValidationSpecificationRelationship[];
  foreign_keys?: ValidationSpecificationForeignKey[];
  constraints?: ValidationSpecificationConstraint[];

  dependencies?: unknown[];
  statistical_behavior?: unknown[];
  scenarios?: unknown[];
}

export interface ValidationSpecificationEntity {
  name?: string;
  population?: {
    count?: number;
  };
  fields?: ValidationSpecificationField[];
  identity?: {
    fields?: string[];
  };
}

export interface ValidationSpecificationField {
  name?: string;
  type?: string;
  identity?: {
    strategy?: string;
  };
}

export interface ValidationSpecificationRelationship {
  source?: string;
  target?: string;
  type?: string;
  source_participation?: string;
  target_participation?: string;
}

export interface ValidationSpecificationForeignKey {
  name?: string;
  source?: {
    entity?: string;
    fields?: string[];
  };
  target?: {
    entity?: string;
    fields?: string[];
  };
}

export interface ValidationSpecificationConstraint {
  entity?: string;
  field?: string;
  operator?: string;
  value?: number;
}

@Injectable({
  providedIn: 'root',
})
export class ValidationDataService {
  private readonly specificationUrl =
    '/specification.json';

  async load(): Promise<ValidationSpecification> {
    const response =
      await fetch(this.specificationUrl);

    if (!response.ok) {
      throw new Error(
        `Unable to load specification: ${response.status}`,
      );
    }

    return response.json() as Promise<ValidationSpecification>;
  }
}
