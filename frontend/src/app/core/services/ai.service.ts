/**
 * File: ai.service.ts
 * Purpose: Provides frontend access to FORGE AI capabilities.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import {
  HttpClient,
  HttpContext,
} from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { AICapability } from '../interfaces/ai-capability.interface';
import {
  AIFieldProposalRequest,
  AIFieldProposalResponse,
} from '../interfaces/ai-field-proposal.interface';
import { AISemanticPreview } from '../interfaces/ai-semantic-preview.interface';
import { AIDataModelProposal } from '../interfaces/ai-data-model-proposal.interface';
import { AIIdentityProposalRequest, AIIdentityProposalResponse } from '../interfaces/ai-identity-proposal.interface';
import {
  AIRelationshipProposal,
  AIRelationshipProposalRequest,
  AIRelationshipProposalResponse,
} from '../interfaces/ai-relationship-proposal.interface';
import {
  AIConstraintProposalRequest,
  AIConstraintProposalResponse,
} from '../interfaces/ai-constraint-proposal.interface';
import {
  AIForeignKeyProposalRequest,
  AIForeignKeyProposalResponse,
} from '../interfaces/ai-foreign-key-proposal.interface';
import { AIDataModelProposalResponse } from '../interfaces/ai-data-model-proposal-response.interface';
import { AIEntityProposal } from '../interfaces/ai-entity-proposal.interface';
import { ApiLoadingMessage } from '../enums/api-loading-message.enum';
import { API_LOADING_MESSAGE } from '../tokens/api-loading-message.token';
import { API_LOADING_SKIP } from '../tokens/api-loading-skip.token';

@Injectable({
  providedIn: 'root',
})
export class AIService {
  private readonly http = inject(HttpClient);

  getCapabilities(): Observable<AICapability> {
    return this.http.get<AICapability>(
      '/api/v1/ai/capabilities',
      {
        context: new HttpContext().set(
          API_LOADING_SKIP,
          true,
        ),
      },
    );
  }

  previewSemanticValues(
    description: string,
  ): Observable<AISemanticPreview> {
    return this.http.post<{
      status: AISemanticPreview['status'];
      message: string;
      preview_values: string[];
    }>(
      '/api/v1/ai/semantic/preview',
      { description },
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.GeneratingSemanticPreviewWithAI,
        ),
      },
    ).pipe(
      map((response) => ({
        status: response.status,
        message: response.message,
        previewValues: response.preview_values,
      })),
    );
  }

  proposeField(
    request: AIFieldProposalRequest,
  ): Observable<AIFieldProposalResponse> {
    return this.http
      .post<{
        proposal_id: string;
        status: AIFieldProposalResponse['status'];
        message: string;
        proposal: AIFieldProposalResponse['proposal'];
      }>(
        '/api/v1/ai/fields/propose',
        {
          data_model_id: request.dataModelId,
          regenerate: request.regenerate ?? false,
          mode: request.mode,
          entity_name: request.entityName,
          request: request.request,
          existing_field: request.existingField ?? null,
        },
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.GeneratingFieldProposalWithAI,
          ),
        },
      )
      .pipe(
        map((response): AIFieldProposalResponse => ({
          proposalId: response.proposal_id,
          status: response.status,
          message: response.message,
          proposal: response.proposal,
        })),
      );
  }

  proposeIdentity(
    request: AIIdentityProposalRequest,
  ): Observable<AIIdentityProposalResponse> {
    return this.http
      .post<{
        proposal_id: string;
        status: AIIdentityProposalResponse['status'];
        message: string;
        proposal: AIIdentityProposalResponse['proposal'];
      }>(
      '/api/v1/ai/identity/propose',
      {
        data_model_id: request.dataModelId,
        regenerate: request.regenerate ?? false,
        mode: request.mode,
        entity_name: request.entityName,
        fields: request.fields,
        request: request.request,
        existing_identity: request.existingIdentity ?? null,
      },
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.GeneratingIdentityProposalWithAI,
        ),
      },
    )
    .pipe(
      map((response): AIIdentityProposalResponse => ({
        proposalId: response.proposal_id,
        status: response.status,
        message: response.message,
        proposal: response.proposal,
      })),
    );
  }


  proposeRelationship(
    request: AIRelationshipProposalRequest,
  ): Observable<AIRelationshipProposalResponse> {
    interface AIRelationshipProposalApiResponse {
      proposal_id: string;
      status: AIRelationshipProposalResponse['status'];
      message: string;
      proposal: {
        source_entity: string;
        source_field: string;
        target_entity: string;
        target_field: string;
        type: AIRelationshipProposal['type'];
        source_participation: AIRelationshipProposal['sourceParticipation'];
        target_participation: AIRelationshipProposal['targetParticipation'];
      } | null;
    }

    return this.http
      .post<AIRelationshipProposalApiResponse>(
        '/api/v1/ai/relationships/propose',
        {
          data_model_id: request.dataModelId,
          regenerate: request.regenerate ?? false,
          mode: request.mode,
          entities: request.entities,
          request: request.request,
          existing_relationship:
            request.existingRelationship ?? null,
        },
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.GeneratingRelationshipProposalWithAI,
          ),
        },
      )
      .pipe(
        map((response): AIRelationshipProposalResponse => ({
          proposalId: response.proposal_id,
          status: response.status,
          message: response.message,
          proposal: response.proposal
            ? {
                sourceEntity: response.proposal.source_entity,
                sourceField: response.proposal.source_field,
                targetEntity: response.proposal.target_entity,
                targetField: response.proposal.target_field,
                type: response.proposal.type,
                sourceParticipation:
                  response.proposal.source_participation,
                targetParticipation:
                  response.proposal.target_participation,
              }
            : null,
        })),
      );
  }

  proposeForeignKey(
    request: AIForeignKeyProposalRequest,
  ): Observable<AIForeignKeyProposalResponse> {
    interface AIForeignKeyProposalApiResponse {
      proposal_id: string;
      status: AIForeignKeyProposalResponse['status'];
      message: string;
      proposal: {
        source_entity: string;
        source_fields: string[];
        target_entity: string;
      } | null;
    }

    return this.http
      .post<AIForeignKeyProposalApiResponse>(
        '/api/v1/ai/foreign-keys/propose',
        {
          data_model_id: request.dataModelId,
          regenerate: request.regenerate ?? false,
          mode: request.mode,
          entities: request.entities,
          request: request.request,
          existing_foreign_key:
            request.existingForeignKey ?? null,
        },
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.GeneratingForeignKeyProposalWithAI,
          ),
        },
      )
      .pipe(
        map((response): AIForeignKeyProposalResponse => ({
          proposalId: response.proposal_id,
          status: response.status,
          message: response.message,
          proposal: response.proposal
            ? {
                sourceEntity: response.proposal.source_entity,
                sourceFields: response.proposal.source_fields,
                targetEntity: response.proposal.target_entity,
              }
            : null,
        })),
      );
  }

  proposeConstraint(
    request: AIConstraintProposalRequest,
  ): Observable<AIConstraintProposalResponse> {
    return this.http
      .post<{
        proposal_id: string;
        status: AIConstraintProposalResponse['status'];
        message: string;
        proposal: AIConstraintProposalResponse['proposal'];
      }>(
      '/api/v1/ai/constraints/propose',
      {
        data_model_id: request.dataModelId,
        regenerate: request.regenerate ?? false,
        mode: request.mode,
        entities: request.entities,
        request: request.request,
        existing_constraint: request.existingConstraint ?? null,
      },
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.GeneratingConstraintProposalWithAI,
        ),
      },
    )
    .pipe(
      map((response): AIConstraintProposalResponse => ({
        proposalId: response.proposal_id,
        status: response.status,
        message: response.message,
        proposal: response.proposal,
      })),
    );
  }

  recordProposalActivity(
    dataModelId: string,
    proposalType:
      | 'entity'
      | 'identity'
      | 'relationship'
      | 'foreign key'
      | 'constraint'
      | 'field',
    action: 'ACCEPTED' | 'REGENERATED' | 'DISMISSED',
    proposalId: string,
  ): Observable<void> {
    return this.http.post<void>(
      '/api/v1/ai/proposals/activity',
      {
        data_model_id: dataModelId,
        proposal_type: proposalType,
        proposal_id: proposalId,
        action,
      },
      {
        context: new HttpContext().set(
          API_LOADING_SKIP,
          true,
        ),
      },
    );
  }

  proposeEntity(
    dataModelId: string,
    prompt: string,
    regenerate = false,
  ): Observable<AIEntityProposal> {
    return this.http
      .post<{
        proposal_id: string;
        name: string;
        description: string;
        population: number;
        reasoning: string;
      }>(
      '/api/v1/ai/entities/propose',
      { data_model_id: dataModelId, prompt, regenerate },
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.GeneratingEntityProposalWithAI,
        ),
      },
    )
    .pipe(
      map((response): AIEntityProposal => ({
        proposalId: response.proposal_id,
        name: response.name,
        description: response.description,
        population: response.population,
        reasoning: response.reasoning,
      })),
    );
  }

  recordDataModelProposalAccepted(proposalId: string): Observable<void> {
    return this.http.post<void>(
      '/api/v1/ai/data-models/proposals/activity',
      { action: 'ACCEPTED', proposal_id: proposalId },
      {
        context: new HttpContext().set(API_LOADING_SKIP, true),
      },
    );
  }

  suggestDataModel(
    prompt: string,
    regenerate = false,
  ): Observable<AIDataModelProposal> {
    return this.http
      .post<AIDataModelProposalResponse>(
        '/api/v1/ai/data-models/suggest',
        { prompt, regenerate },
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.GeneratingDataModelWithAI,
          ),
        },
      )
      .pipe(
        map((response) => ({
          proposalId: response.proposal_id,
          name: response.name,
          description: response.description,
          suggestedTags: response.suggested_tags,
          reasoning: response.reasoning,
        })),
      );
  }
}
