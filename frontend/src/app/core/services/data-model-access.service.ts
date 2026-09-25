/**
 * File: data-model-access.service.ts
 * Purpose: API operations for Data Model collaboration access.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  DataModelAccess,
  DataModelAccessRole,
} from '../interfaces/data-model-access.interface';

interface DataModelAccessResponse {
  data_model_id: string;
  user_id: string;
  display_name: string;
  email: string;
  role: DataModelAccessRole;
  granted_at: string;
}

interface GrantDataModelAccessRequest {
  user_id: string;
  role: DataModelAccessRole;
}

interface UpdateDataModelAccessRequest {
  role: 'CONTRIBUTOR' | 'VIEWER';
}


@Injectable({
  providedIn: 'root',
})
export class DataModelAccessService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = environment.apiBaseUrl;

  grantAccess(
    dataModelId: string,
    userId: string,
    role: DataModelAccessRole,
  ): Observable<DataModelAccess> {
    const request: GrantDataModelAccessRequest = {
      user_id: userId,
      role,
    };

    return this.http
      .post<DataModelAccessResponse>(
        `${this.apiBaseUrl}/data-models/${dataModelId}/access`,
        request,
      )
      .pipe(
        map((access) => this.mapAccess(access)),
      );
  }

  getAccess(
    dataModelId: string,
  ): Observable<DataModelAccess[]> {
    return this.http
      .get<DataModelAccessResponse[]>(
        `${this.apiBaseUrl}/data-models/${dataModelId}/access`,
      )
      .pipe(
        map((accessRecords) =>
          accessRecords.map((access) => this.mapAccess(access)),
        ),
      );
  }

  private mapAccess(
    access: DataModelAccessResponse,
  ): DataModelAccess {
    return {
      dataModelId: access.data_model_id,
      userId: access.user_id,
      displayName: access.display_name,
      email: access.email,
      role: access.role,
      grantedAt: access.granted_at,
    };
  }

  updateRole(
    dataModelId: string,
    userId: string,
    role: 'CONTRIBUTOR' | 'VIEWER',
  ): Observable<DataModelAccess> {
    const request: UpdateDataModelAccessRequest = {
      role,
    };

    return this.http
      .put<DataModelAccessResponse>(
        `${this.apiBaseUrl}/data-models/${dataModelId}/access/${userId}`,
        request,
      )
      .pipe(map((access) => this.mapAccess(access)));
  }



  revokeAccess(
    dataModelId: string,
    userId: string,
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.apiBaseUrl}/data-models/${dataModelId}/access/${userId}`,
    );
  }


}
