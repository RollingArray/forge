import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  GenerationArtifact,
  GenerationArtifactPreview,
} from '../../results/results.models';

import { environment } from '../../../../environments/environment';
import {
  GenerationJobResponse,
  GenerationReadiness,
} from '../models/generation.models';

@Injectable({
  providedIn: 'root',
})
export class GenerationService {
  private readonly http = inject(HttpClient);
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
