import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';

import { SseService } from '../../../core/services/sse.service';
import { GenerationCheckpoint } from '../../../shared/models/generation-checkpoint.models';

import {
  GenerationArtifact,
  GenerationArtifactPreview,
} from '../../results/results.models';

import { environment } from '../../../../environments/environment';
import {
  GenerationChunkCommittedEvent,
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
    );
  }

  createGenerationJob(
    dataModelId: string,
  ): Observable<GenerationJobResponse> {
    return this.http.post<GenerationJobResponse>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation`,
      {},
    );
  }


  startGenerationJob(
    dataModelId: string,
    jobId: string,
  ): Observable<GenerationJobResponse> {
    return this.http.post<GenerationJobResponse>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/start`,
      {},
    );
  }


  getGenerationJob(
    dataModelId: string,
    jobId: string,
  ): Observable<GenerationJobResponse> {
    return this.http.get<GenerationJobResponse>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}`,
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
    );
  }

  getGenerationArtifacts(
    dataModelId: string,
    jobId: string,
  ): Observable<GenerationArtifact[]> {
    return this.http.get<GenerationArtifact[]>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/artifacts`,
    );
  }

  getGenerationArtifactPreview(
    dataModelId: string,
    jobId: string,
    entityName: string,
  ): Observable<GenerationArtifactPreview> {
    return this.http.get<GenerationArtifactPreview>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/artifacts/${encodeURIComponent(entityName)}/preview`,
    );
  }

  downloadGenerationArtifact(
    dataModelId: string,
    jobId: string,
    entityName: string,
  ): Observable<Blob> {
    return this.http.get(
      `${this.apiBaseUrl}/data-models/${dataModelId}/generation/${jobId}/artifacts/${encodeURIComponent(entityName)}/download`,
      { responseType: 'blob' },
    );
  }

}
