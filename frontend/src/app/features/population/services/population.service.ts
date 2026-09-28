import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import {
  PopulationCandidatePlan,
  PopulationPlan,
} from '../models/population.models';

@Injectable({
  providedIn: 'root',
})
export class PopulationService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = environment.apiBaseUrl;

  getPopulationPlan(dataModelId: string): Observable<PopulationPlan> {
    return this.http.get<PopulationPlan>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/population-plan`,
    );
  }

  acceptPopulationPlan(
    dataModelId: string,
    populations: Record<string, number>,
  ): Observable<unknown> {
    return this.http.post(
      `${this.apiBaseUrl}/data-models/${dataModelId}/population-plan/accept`,
      {
        populations,
      },
    );
  }

  buildCandidatePlan(
    dataModelId: string,
    target: number,
    driver: string,
  ): Observable<PopulationCandidatePlan> {
    return this.http.post<PopulationCandidatePlan>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/population-plan/candidate`,
      {
        target,
        driver,
      },
    );
  }
}
