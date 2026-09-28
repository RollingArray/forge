import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

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
}
