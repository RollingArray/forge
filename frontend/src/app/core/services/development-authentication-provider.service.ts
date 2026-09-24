/**
 * File: development-authentication-provider.service.ts
 * Purpose: Development authentication provider for FORGE.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { AuthSession } from '../interfaces/auth-session.interface';
import { AuthenticationProvider } from '../interfaces/authentication-provider.interface';
import { LoginRequest } from '../interfaces/login-request.interface';

@Injectable({
  providedIn: 'root',
})
export class DevelopmentAuthenticationProviderService
  implements AuthenticationProvider
{
  private readonly authenticationEndpoint =
    'http://127.0.0.1:8000/api/v1/auth/login';

  constructor(
    private readonly http: HttpClient,
  ) {}

  async login(request: LoginRequest): Promise<AuthSession> {
    try {
      return await firstValueFrom(
        this.http.post<AuthSession>(
          this.authenticationEndpoint,
          request,
        ),
      );
    } catch (error) {
      if (error instanceof HttpErrorResponse) {
        throw error;
      }

      throw new Error('Authentication request failed.');
    }
  }

  async logout(): Promise<void> {
    return;
  }

  getSession(): AuthSession | null {
    return null;
  }
}
