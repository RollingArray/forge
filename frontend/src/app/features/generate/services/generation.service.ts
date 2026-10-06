import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpContext } from '@angular/common/http';
import { map, Observable } from 'rxjs';

import { SseService } from '../../../core/services/sse.service';
import { GenerationCheckpoint } from '../../../shared/models/generation-checkpoint.models';

import {
  GenerationArtifact,
  GenerationArtifactPreview,
} from '../../results/results.models';

import { environment } from '../../../../environments/environment';
import { ApiLoadingMessage } from '../../../core/enums/api-loading-message.enum';
import { API_LOADING_MESSAGE } from '../../../core/tokens/api-loading-message.token';
import {
  GenerationChunkCommittedEvent,
  GenerationActivityEvent,
  GenerationCompletedEvent,
  GenerationEntityCompletedEvent,
  GenerationSemanticCallStartedEvent,
  GenerationJobResponse,
  GenerationReadiness,
  GenerationSseEvent,
} from '../models/generation.models';

@Injectable({
  providedIn: 'root',
})
export class GenerationService {
  private readonly http = inject(HttpClient);
  private readonly sse = inject(SseService);
  private readonly apiBaseUrl = environment.apiBaseUrl;

  getGenerationReadiness(
    dataModelId: string,
  ): Observable<GenerationReadiness> {
    return this.http.get<GenerationReadiness>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/readiness`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.LoadingGenerationReadiness,
        ),
      },
    );
  }

  createGenerationJob(
    dataModelId: string,
  ): Observable<GenerationJobResponse> {
    return this.http.post<GenerationJobResponse>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation`,
      {},
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.CreatingGenerationJob,
        ),
      },
    );
  }


  startGenerationJob(
    dataModelId: string,
    jobId: string,
  ): Observable<GenerationJobResponse> {
    return this.http.post<GenerationJobResponse>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/start`,
      {},
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.StartingGeneration,
        ),
      },
    );
  }


  getGenerationJob(
    dataModelId: string,
    jobId: string,
  ): Observable<GenerationJobResponse> {
    return this.http.get<GenerationJobResponse>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.LoadingGenerationJob,
        ),
      },
    );
  }

  connectToGenerationEvents(
    dataModelId: string,
    jobId: string,
  ): Observable<GenerationSseEvent> {
    return this.sse
      .connect(
        `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/events`,
      )
      .pipe(
        map((event) => {
          if (event.type === 'JOB_SNAPSHOT') {
            return {
              type: 'JOB_SNAPSHOT',
              data: JSON.parse(event.data) as GenerationJobResponse,
            };
          }

          if (event.type === 'CHUNK_COMMITTED') {
            return {
              type: 'CHUNK_COMMITTED',
              data: JSON.parse(
                event.data,
              ) as GenerationChunkCommittedEvent,
            };
          }

          if (event.type === 'SEMANTIC_CALL_STARTED') {
            return {
              type: 'SEMANTIC_CALL_STARTED',
              data: JSON.parse(
                event.data,
              ) as GenerationSemanticCallStartedEvent,
            };
          }

          if (event.type === 'GENERATION_ACTIVITY') {
            return {
              type: 'GENERATION_ACTIVITY',
              data: JSON.parse(
                event.data,
              ) as GenerationActivityEvent,
            };
          }

          if (event.type === 'ENTITY_COMPLETED') {
            return {
              type: 'ENTITY_COMPLETED',
              data: JSON.parse(
                event.data,
              ) as GenerationEntityCompletedEvent,
            };
          }

          if (event.type === 'GENERATION_COMPLETED') {
            return {
              type: 'GENERATION_COMPLETED',
              data: JSON.parse(
                event.data,
              ) as GenerationCompletedEvent,
            };
          }

          throw new Error(
            `Unsupported generation SSE event: ${event.type}`,
          );
        }),
      );
  }

  getGenerationCheckpoint(
    dataModelId: string,
    jobId: string,
  ): Observable<GenerationCheckpoint> {
    return this.http.get<GenerationCheckpoint>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/checkpoint`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.LoadingGenerationCheckpoint,
        ),
      },
    );
  }

  getGenerationArtifacts(
    dataModelId: string,
    jobId: string,
  ): Observable<GenerationArtifact[]> {
    return this.http.get<GenerationArtifact[]>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/artifacts`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.LoadingGeneratedFiles,
        ),
      },
    );
  }

  getGenerationArtifactPreview(
    dataModelId: string,
    jobId: string,
    entityName: string,
  ): Observable<GenerationArtifactPreview> {
    return this.http.get<GenerationArtifactPreview>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/artifacts/${encodeURIComponent(entityName)}/preview`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.LoadingArtifactPreview,
        ),
      },
    );
  }

  downloadGenerationArtifact(
    dataModelId: string,
    jobId: string,
    entityName: string,
  ): Observable<Blob> {
    return this.http.get(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/artifacts/${encodeURIComponent(entityName)}/download`,
      {
        responseType: 'blob',
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.DownloadingGeneratedFile,
        ),
      },
    );
  }

}
