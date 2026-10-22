import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ApiLoadingMessage } from '../enums/api-loading-message.enum';
import { API_LOADING_MESSAGE } from '../tokens/api-loading-message.token';
import { CreateFavoriteRequest, Favorite } from '../interfaces/favorite.interface';

@Injectable({ providedIn: 'root' })
export class FavoritesService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = environment.apiBaseUrl;

  getFavorites(): Observable<Favorite[]> {
    return this.http.get<Favorite[]>(`${this.apiBaseUrl}/favorites`, {
      context: new HttpContext().set(
        API_LOADING_MESSAGE,
        ApiLoadingMessage.LoadingFavorites,
      ),
    });
  }

  addFavorite(request: CreateFavoriteRequest): Observable<Favorite> {
    return this.http.post<Favorite>(`${this.apiBaseUrl}/favorites`, request, {
      context: new HttpContext().set(
        API_LOADING_MESSAGE,
        ApiLoadingMessage.CreatingFavorite,
      ),
    });
  }

  removeFavorite(favoriteId: string): Observable<void> {
    return this.http.delete<void>(
      `${this.apiBaseUrl}/favorites/${encodeURIComponent(favoriteId)}`,
      {
        context: new HttpContext().set(
          API_LOADING_MESSAGE,
          ApiLoadingMessage.DeletingFavorite,
        ),
      },
    );
  }
}
