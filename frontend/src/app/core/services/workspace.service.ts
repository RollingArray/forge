/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: workspace.service.ts
 * Purpose: Loads Workspace data from the FORGE API.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, forkJoin, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ApiLoadingMessage } from '../enums/api-loading-message.enum';
import { API_LOADING_MESSAGE } from '../tokens/api-loading-message.token';

import { ActivityResponse } from '../interfaces/activity-response.interface';
import { Activity } from '../interfaces/activity.interface';
import { CreateDataModelRequest } from '../interfaces/create-data-model-request.interface';
import { DataModelResponse } from '../interfaces/data-model-response.interface';
import { DataModelListItemResponse } from '../interfaces/data-model-list-item-response.interface';
import { DataModel } from '../interfaces/data-model.interface';
import { Metric } from '../interfaces/metric.interface';
import { TemplateResponse } from '../interfaces/template-response.interface';
import { Template } from '../interfaces/template.interface';
import { UpdateDataModelRequest } from '../interfaces/update-data-model-request.interface';
import { WorkspaceData } from '../interfaces/workspace-data.interface';
import { WorkspaceMetricsResponse } from '../interfaces/workspace-metrics-response.interface';

@Injectable({
  providedIn: 'root',
})
export class WorkspaceService {
  private readonly http = inject(HttpClient);

  private readonly apiBaseUrl = environment.apiBaseUrl;

  loadWorkspace(): Observable<WorkspaceData> {
    return forkJoin({
      metrics: this.http.get<WorkspaceMetricsResponse>(
        `${this.apiBaseUrl}/workspace/metrics`,
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.LoadingWorkspace,
          ),
        },
      ),
      dataModels: this.http.get<DataModelListItemResponse[]>(
        `${this.apiBaseUrl}/data-models`,
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.LoadingWorkspace,
          ),
        },
      ),
      templates: this.http.get<TemplateResponse[]>(
        `${this.apiBaseUrl}/workspace/templates`,
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.LoadingWorkspace,
          ),
        },
      ),
      activities: this.http.get<ActivityResponse[]>(
        `${this.apiBaseUrl}/workspace/activity`,
        {
          context: new HttpContext().set(
            API_LOADING_MESSAGE,
            ApiLoadingMessage.LoadingWorkspace,
          ),
        },
      ),
    }).pipe(
      map((response) => ({
        metrics: this.mapMetrics(response.metrics),
        dataModels: response.dataModels.map((dataModel) =>
          this.mapDataModel(dataModel),
        ),
        templates: response.templates.map((template) => ({
          name: template.name,
          description: template.description,
          icon: template.icon,
          accent: template.accent,
        })),
        activities: response.activities.map((activity) => ({
          action: activity.action,
          dataModel: activity.data_model,
          time: activity.time,
          icon: activity.icon,
          accent: activity.accent,
        })),
      })),
    );
  }

  createDataModel(
    request: CreateDataModelRequest,
  ): Observable<DataModelResponse> {
    return this.http.post<DataModelResponse>(
      `${this.apiBaseUrl}/data-models`,
      request,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.CreatingDataModel,
        ),
      },
    );
  }

  updateDataModel(
    dataModelId: string,
    request: UpdateDataModelRequest,
  ): Observable<DataModelResponse> {
    return this.http.put<DataModelResponse>(
      `${this.apiBaseUrl}/data-models/${dataModelId}`,
      request,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.UpdatingDataModel,
        ),
      },
    );
  }

  deleteDataModel(dataModelId: string): Observable<void> {
    return this.http.delete<void>(
      `${this.apiBaseUrl}/data-models/${dataModelId}`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.DeletingDataModel,
        ),
      },
    );
  }

  private mapMetrics(response: WorkspaceMetricsResponse): Metric[] {
    return [
      {
        label: 'Total Data Models',
        value: String(response.total_data_models),
        icon: 'deployed_code',
        accent: 'purple',
        supportingText: 'Across your workspace',
        supportingType: 'subtle',
      },
      {
        label: 'Total Entities',
        value: String(response.total_entities),
        icon: 'database',
        accent: 'blue',
        supportingText: 'Across your data models',
        supportingType: 'subtle',
      },
      {
        label: 'Generated Datasets',
        value: String(response.generated_datasets),
        icon: 'dataset',
        accent: 'green',
        supportingText: 'Generated successfully',
        supportingType: 'positive',
      },
      {
        label: 'Total Records',
        value: String(response.total_records),
        icon: 'table_rows',
        accent: 'orange',
        supportingText: 'Across generated datasets',
        supportingType: 'subtle',
      },
    ];
  }

  private mapDataModel(response: DataModelListItemResponse): DataModel {
    return {
      dataModelId: response.data_model_id,
      ownerUserId: response.owner_user_id,
      accessRole: response.access_role,
      name: response.name,
      description: response.description,
      color: response.color,
      tags: response.tags ?? [],
      entities: 0,
      relationships: 0,
      updated: this.formatUpdated(response.updated_at),
      status: response.status,
    };
  }

  private formatUpdated(value: string): string {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return '';
    }

    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  }
}
