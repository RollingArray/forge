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
          ApiLoadingMessage.Loading,
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
            ApiLoadingMessage.Loading,
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
