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
import { AISemanticPreview } from '../interfaces/ai-semantic-preview.interface';
import { AIDataModelProposal } from '../interfaces/ai-data-model-proposal.interface';
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
