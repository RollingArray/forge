import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpContext } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { ApiLoadingMessage } from '../../../core/enums/api-loading-message.enum';
import { API_LOADING_MESSAGE } from '../../../core/tokens/api-loading-message.token';
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
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.LoadingPopulationPlan,
        ),
      },
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
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.SavingPopulationPlan,
        ),
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
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.BuildingCandidatePopulationPlan,
        ),
      },
    );
  }
}
