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
import { AIDataModelProposalResponse } from '../interfaces/ai-data-model-proposal-response.interface';
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
        status: AIFieldProposalResponse['status'];
        message: string;
        proposal: AIFieldProposalResponse['proposal'];
      }>(
        '/api/v1/ai/fields/propose',
        {
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
      );
  }

  proposeIdentity(
    request: AIIdentityProposalRequest,
  ): Observable<AIIdentityProposalResponse> {
    return this.http.post<AIIdentityProposalResponse>(
      '/api/v1/ai/identity/propose',
      {
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
    );
  }

  suggestDataModel(prompt: string): Observable<AIDataModelProposal> {
    return this.http
      .post<AIDataModelProposalResponse>(
        '/api/v1/ai/data-models/suggest',
        { prompt },
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.GeneratingDataModelWithAI,
          ),
        },
      )
      .pipe(
        map((response) => ({
          name: response.name,
          description: response.description,
          suggestedTags: response.suggested_tags,
          reasoning: response.reasoning,
        })),
      );
  }
}
