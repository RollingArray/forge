import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthSession } from '../interfaces/auth-session.interface';
import { API_LOADING_SKIP } from '../tokens/api-loading-skip.token';

export interface MagicLinkRequestResponse {
  message: string;
}

@Injectable({
  providedIn: 'root',
})
export class MagicLinkService {
  private readonly endpoint = `${environment.apiBaseUrl}/auth/magic-link`;

  private readonly publicRequestContext = new HttpContext().set(
    API_LOADING_SKIP,
    true,
  );

  constructor(private readonly http: HttpClient) {}

  requestLink(email: string): Promise<MagicLinkRequestResponse> {
    return firstValueFrom(
      this.http.post<MagicLinkRequestResponse>(
        this.endpoint,
        { email },
        { context: this.publicRequestContext },
      ),
    );
  }

  verifyToken(token: string): Promise<AuthSession> {
    return firstValueFrom(
      this.http.post<AuthSession>(
        `${this.endpoint}/verify`,
        { token },
        { context: this.publicRequestContext },
      ),
    );
  }
}
