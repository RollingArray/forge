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
import { ForgeConstraint } from '../interfaces/forge-constraint.interface';
import { ForgeForeignKey } from '../interfaces/forge-foreign-key.interface';
import { ForgeSpecification } from '../interfaces/forge-specification.interface';
import { ForgeSpecificationDependency } from '../interfaces/forge-specification-dependency.interface';
import { ForgeSpecificationEntity } from '../interfaces/forge-specification-entity.interface';
import { ForgeSpecificationField } from '../interfaces/forge-specification-field.interface';
import { ForgeSpecificationGeneration } from '../interfaces/forge-specification-generation.interface';
import { ForgeSpecificationModel } from '../interfaces/forge-specification-model.interface';
import { ForgeSpecificationRelationship } from '../interfaces/forge-specification-relationship.interface';
import { ForgeRelationshipEndpointValue } from '../types/forge-relationship-endpoint-value.type';
import {
  SpecificationValidationResult,
} from '../interfaces/specification-validation.interface';
import { SpecificationReplacementCsv } from '../interfaces/specification-replacement-csv.interface';
import { SpecificationReplacementPreviewResponse } from '../interfaces/specification-replacement-preview-response.interface';
import { SpecificationReplacementApplyRequest } from '../interfaces/specification-replacement-apply-request.interface';
import { SpecificationReplacementApplyResponse } from '../interfaces/specification-replacement-apply-response.interface';
import { SpecificationReplacementValidationResponse } from '../interfaces/specification-replacement-validation-response.interface';


type PopulationScaling = 'FIXED' | 'SCALABLE';

interface CreateEntityRequest {
  name: string;
  description: string;
  population: {
    count: number;
    scaling: PopulationScaling;
  };
}

interface UpdateEntityRequest {
  description: string;
  population: number;
  scaling: PopulationScaling;
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

interface CreateForeignKeyRequest {
  source_entity: string;
  source_fields: string[];
  target_entity: string;
}

interface UpdateForeignKeyRequest {
  existing: {
    name: string;
  };
  foreign_key: CreateForeignKeyRequest;
}

interface DeleteForeignKeyRequest {
  name: string;
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

interface UpdateRelationshipRequest {
  existing: DeleteRelationshipRequest;
  relationship: CreateRelationshipRequest;
}

interface DeleteRelationshipRequest {
  source: ForgeRelationshipEndpointValue;
  target: ForgeRelationshipEndpointValue;
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

  exportReplacement(
    dataModelId: string,
  ): Observable<SpecificationReplacementCsv> {
    return this.http.get<SpecificationReplacementCsv>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/replacement/export`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.ExportingSpecificationReplacement,
        ),
      },
    );
  }

  previewReplacement(
    dataModelId: string,
    csv: SpecificationReplacementCsv,
  ): Observable<SpecificationReplacementPreviewResponse> {
    return this.http.post<SpecificationReplacementPreviewResponse>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/replacement/preview`,
      { csv },
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.PreviewingSpecificationReplacement,
        ),
      },
    );
  }

  validateReplacement(
    dataModelId: string,
    request: SpecificationReplacementApplyRequest,
  ): Observable<{
    baseRevision: string;
    csvDigest: string;
    summary: Record<string, number>;
    validation: SpecificationValidationResult;
    specification: ForgeSpecification;
  }> {
    return this.http
      .post<SpecificationReplacementValidationResponse>(
        `${this.apiBaseUrl}/data-models/${dataModelId}/specification/replacement/validate`,
        request,
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.ValidatingDataModel,
          ),
        },
      )
      .pipe(
        map((response) => ({
          baseRevision: response.base_revision,
          csvDigest: response.csv_digest,
          summary: response.summary,
          validation: {
            modelName: response.validation.model_name,
            specificationVersion: response.validation.specification_version,
            vocabularyVersion: response.validation.vocabulary_version,
            errors: response.validation.errors,
            warnings: response.validation.warnings,
            unsupported: response.validation.unsupported,
            passed: response.validation.passed,
            totalChecks: response.validation.total_checks,
            entitiesValidated: response.validation.entities_validated,
            canContinue: response.validation.can_continue,
            findings: response.validation.findings,
            entities: response.validation.entities,
          },
          specification: this.mapSpecification(
            response.specification as unknown as SpecificationResponse,
          ),
        })),
      );
  }

  applyReplacement(
    dataModelId: string,
    request: SpecificationReplacementApplyRequest,
  ): Observable<SpecificationReplacementApplyResponse> {
    return this.http.post<SpecificationReplacementApplyResponse>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/replacement/apply`,
      request,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.ApplyingSpecificationReplacement,
        ),
      },
    );
  }

  validate(
    dataModelId: string,
  ): Observable<SpecificationValidationResult> {
    return this.http
      .get<{
        model_name: string;
        specification_version: string;
        vocabulary_version: string;
        errors: number;
        warnings: number;
        unsupported: number;
        passed: number;
        total_checks: number;
        entities_validated: number;
        can_continue: boolean;
        findings: SpecificationValidationResult['findings'];
        entities: SpecificationValidationResult['entities'];
      }>(
        `${this.apiBaseUrl}/data-models/${dataModelId}/specification/validation`,
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.ValidatingDataModel,
          ),
        },
      )
      .pipe(
        map((response) => ({
          modelName: response.model_name,
          specificationVersion: response.specification_version,
          vocabularyVersion: response.vocabulary_version,
          errors: response.errors,
          warnings: response.warnings,
          unsupported: response.unsupported,
          passed: response.passed,
          totalChecks: response.total_checks,
          entitiesValidated: response.entities_validated,
          canContinue: response.can_continue,
          findings: response.findings,
          entities: response.entities,
        })),
      );
  }

  createEntity(
    dataModelId: string,
    name: string,
    description: string,
    population: number,
    scaling: PopulationScaling = 'SCALABLE',
  ): Observable<ForgeSpecificationEntity> {
    return this.http.post<ForgeSpecificationEntity>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/entities`,
      {
        name,
        description,
        population: {
          count: population,
          scaling,
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

  deleteEntity(dataModelId: string, entityName: string): Observable<void> {
    return this.http.delete<void>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/entities/${encodeURIComponent(entityName)}`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.LoadingSpecification,
        ),
      },
    );
  }

  updateEntity(
    dataModelId: string,
    entityName: string,
    description: string,
    population: number,
    scaling: PopulationScaling,
  ): Observable<ForgeSpecificationEntity> {
    return this.http.put<ForgeSpecificationEntity>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/entities/${encodeURIComponent(entityName)}`,
      { description, population, scaling } satisfies UpdateEntityRequest,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.LoadingSpecification,
        ),
      },
    );
  }

  updateEntityPopulation(
    dataModelId: string,
    entityName: string,
    count: number,
  ): Observable<ForgeSpecificationEntity> {
    return this.http.put<ForgeSpecificationEntity>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/entities/${encodeURIComponent(entityName)}/population`,
      { count },
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.LoadingSpecification,
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

  createForeignKey(
    dataModelId: string,
    request: CreateForeignKeyRequest,
  ): Observable<ForgeForeignKey> {
    return this.http.post<ForgeForeignKey>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/foreign-keys`,
      request,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.CreatingForeignKey,
        ),
      },
    );
  }

  deleteField(
    dataModelId: string,
    entityName: string,
    fieldName: string,
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/entities/${encodeURIComponent(entityName)}/fields/${encodeURIComponent(fieldName)}`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.DeletingField,
        ),
      },
    );
  }

  updateForeignKey(
    dataModelId: string,
    request: UpdateForeignKeyRequest,
  ): Observable<ForgeForeignKey> {
    return this.http.put<ForgeForeignKey>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/foreign-keys`,
      request,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.UpdatingForeignKey,
        ),
      },
    );
  }

  deleteForeignKey(
    dataModelId: string,
    foreignKey: DeleteForeignKeyRequest,
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/foreign-keys`,
      {
        body: foreignKey,
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.DeletingForeignKey,
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

  updateRelationship(
    dataModelId: string,
    request: UpdateRelationshipRequest,
  ): Observable<ForgeSpecificationRelationship> {
    return this.http.put<ForgeSpecificationRelationship>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/relationships`,
      request,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.UpdatingRelationship,
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

  createConstraint(
    dataModelId: string,
    constraint: ForgeConstraint,
  ): Observable<ForgeConstraint> {
    return this.http.post<ForgeConstraint>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/constraints`,
      constraint,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.CreatingConstraint,
        ),
      },
    );
  }

  updateConstraint(
    dataModelId: string,
    request: {
      existing: ForgeConstraint;
      constraint: ForgeConstraint;
    },
  ): Observable<ForgeConstraint> {
    return this.http.put<ForgeConstraint>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/constraints`,
      request,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.UpdatingConstraint,
        ),
      },
    );
  }

  deleteConstraint(
    dataModelId: string,
    constraint: ForgeConstraint,
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/specification/constraints`,
      {
        body: constraint,
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.DeletingConstraint,
        ),
      },
    );
  }

  saveSpecification(
    dataModelId: string,
    specification: Record<string, unknown>,
    source: "manual" | "ai" = "manual",
  ): Observable<ForgeSpecification> {
    return this.http
      .put<SpecificationResponse>(
        `${this.apiBaseUrl}/data-models/${dataModelId}/specification`,
        specification,
        {
          params: { source },
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.SavingSpecification,
          ),
        },
      )
      .pipe(map((response) => this.mapSpecification(response)));
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
