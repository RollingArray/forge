/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: specification.service.ts
 * Purpose: Loads canonical FORGE model specifications from the API.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ApiLoadingMessage } from '../enums/api-loading-message.enum';
import { API_LOADING_MESSAGE } from '../tokens/api-loading-message.token';
import {
  ForgeConstraint,
  ForgeForeignKey,
  ForgeSpecification,
  ForgeSpecificationDependency,
  ForgeSpecificationEntity,
  ForgeSpecificationField,
  ForgeSpecificationGeneration,
  ForgeSpecificationModel,
  ForgeSpecificationRelationship,
} from '../interfaces/forge-specification.interface';

interface CreateEntityRequest {
  name: string;
  population: {
    count: number;
  };
}

interface CreateFieldRequest {
  name: string;
  type:
    | 'IDENTIFIER'
    | 'STRING'
    | 'INTEGER'
    | 'DECIMAL'
    | 'BOOLEAN'
    | 'CATEGORICAL';
  identity?: {
    strategy: 'SEQUENTIAL_ID';
  };
  generation?: {
    strategy: 'RANDOM';
    distribution?: string;
    generator?: string;
    parameters?: Record<string, unknown>;
  };
}

interface UpdateFieldRequest {
  name?: string;
  type?: 
    | 'IDENTIFIER'
    | 'STRING'
    | 'INTEGER'
    | 'DECIMAL'
    | 'BOOLEAN'
    | 'CATEGORICAL';
  identity?: {
    strategy: 'SEQUENTIAL_ID';
  };
  generation?: {
    strategy?: 'RANDOM';
    distribution?: string;
    generator?: string;
    parameters?: Record<string, unknown>;
  };
}

interface CreateRelationshipRequest {
  source_entity: string;
  target_entity: string;
  type:
    | 'ONE_TO_ONE'
    | 'ONE_TO_MANY'
    | 'MANY_TO_ONE'
    | 'MANY_TO_MANY';
  source_participation: 'MANDATORY' | 'OPTIONAL';
  target_participation: 'MANDATORY' | 'OPTIONAL';
}

interface DeleteRelationshipRequest {
  source: string;
  target: string;
  type:
    | 'ONE_TO_ONE'
    | 'ONE_TO_MANY'
    | 'MANY_TO_ONE'
    | 'MANY_TO_MANY';
  source_participation: 'MANDATORY' | 'OPTIONAL';
  target_participation: 'MANDATORY' | 'OPTIONAL';
}

interface SpecificationResponse {
  version: string;
  vocabulary_version: string;
  model: ForgeSpecificationModel;
  generation: ForgeSpecificationGeneration;
  entities: ForgeSpecificationEntity[];
  relationships: ForgeSpecificationRelationship[];
  foreign_keys: ForgeForeignKey[];
  constraints: ForgeConstraint[];
  dependencies: ForgeSpecificationDependency[];
  statistical_behavior: unknown[];
  scenarios: unknown[];
}

@Injectable({
  providedIn: 'root',
})
export class SpecificationService {
  private readonly http = inject(HttpClient);

  private readonly apiBaseUrl = environment.apiBaseUrl;

  createEntity(
    dataModelId: string,
    name: string,
    population: number,
  ): Observable<ForgeSpecificationEntity> {
    return this.http.post<ForgeSpecificationEntity>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/entities`,
      {
        name,
        population: {
          count: population,
        },
      } satisfies CreateEntityRequest,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.CreatingEntity,
        ),
      },
    );
  }

  updateEntityIdentity(
    dataModelId: string,
    entityName: string,
    fields: string[],
  ): Observable<ForgeSpecificationEntity> {
    return this.http.put<ForgeSpecificationEntity>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/entities/${encodeURIComponent(entityName)}/identity`,
      { fields },
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.UpdatingEntityIdentity,
        ),
      },
    );
  }

  createField(
    dataModelId: string,
    entityName: string,
    name: string,
    type:
      | 'IDENTIFIER'
      | 'STRING'
      | 'INTEGER'
      | 'DECIMAL'
      | 'BOOLEAN'
      | 'CATEGORICAL',
    options?: Pick<CreateFieldRequest, 'identity' | 'generation'>,
  ): Observable<ForgeSpecificationField> {
    return this.http.post<ForgeSpecificationField>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/entities/${encodeURIComponent(entityName)}/fields`,
      {
        name,
        type,
        ...options,
      } satisfies CreateFieldRequest,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.CreatingField,
        ),
      },
    );
  }

  updateField(
    dataModelId: string,
    entityName: string,
    fieldName: string,
    updates: UpdateFieldRequest,
  ): Observable<ForgeSpecificationField> {
    return this.http.put<ForgeSpecificationField>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/entities/${encodeURIComponent(entityName)}/fields/${encodeURIComponent(fieldName)}`,
      updates,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.UpdatingField,
        ),
      },
    );
  }

  createRelationship(
    dataModelId: string,
    request: CreateRelationshipRequest,
  ): Observable<ForgeSpecificationRelationship> {
    return this.http.post<ForgeSpecificationRelationship>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/relationships`,
      request,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.CreatingRelationship,
        ),
      },
    );
  }

  deleteRelationship(
    dataModelId: string,
    relationship: DeleteRelationshipRequest,
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/relationships`,
      {
        body: relationship,
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.DeletingRelationship,
        ),
      },
    );
  }

  getSpecification(
    dataModelId: string,
  ): Observable<ForgeSpecification> {
    return this.http
      .get<SpecificationResponse>(
        `${this.apiBaseUrl}/data-models/${dataModelId}/specification`,
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.LoadingSpecification,
          ),
        },
      )
      .pipe(
        map((response) => this.mapSpecification(response)),
      );
  }

  private mapSpecification(
    response: SpecificationResponse,
  ): ForgeSpecification {
    return {
      version: response.version,
      vocabularyVersion: response.vocabulary_version,
      model: response.model,
      generation: response.generation,
      entities: response.entities,
      relationships: response.relationships,
      foreignKeys: response.foreign_keys,
      constraints: response.constraints,
      dependencies: response.dependencies,
      statisticalBehavior: response.statistical_behavior,
      scenarios: response.scenarios,
    };
  }
}
