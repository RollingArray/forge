/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: user.service.ts
 * Purpose: Provides authenticated FORGE user operations.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { UserSearchResult } from '../interfaces/user-search-result.interface';
import { API_LOADING_SKIP } from '../tokens/api-loading-skip.token';

interface UserSearchResultResponse {
  user_id: string;
  email: string;
  display_name: string;
}

@Injectable({
  providedIn: 'root',
})
export class UserService {
  private readonly http = inject(HttpClient);

  private readonly apiBaseUrl = environment.apiBaseUrl;

  searchUsers(query: string): Observable<UserSearchResult[]> {
    return this.http
      .get<UserSearchResultResponse[]>(
        `${this.apiBaseUrl}/users/search`,
        {
          params: {
            q: query,
          },
          context: new HttpContext().set(
            API_LOADING_SKIP,
            true,
          ),
        },
      )
      .pipe(
        map((users) =>
          users.map((user) => ({
            userId: user.user_id,
            email: user.email,
            displayName: user.display_name,
          })),
        ),
      );
  }
}
