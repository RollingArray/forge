/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: auth.service.ts
 * Purpose: Manages the authenticated frontend session.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { Inject, Injectable, signal } from '@angular/core';

import { AuthSession } from '../interfaces/auth-session.interface';
import { AuthenticationProvider } from '../interfaces/authentication-provider.interface';
import { AUTHENTICATION_PROVIDER } from '../interfaces/authentication-provider.token';
import { LoginRequest } from '../interfaces/login-request.interface';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly localStorageKey = 'forge.auth.session';

  private readonly session = signal<AuthSession | null>(
    this.loadStoredSession(),
  );

  constructor(
    @Inject(AUTHENTICATION_PROVIDER)
    private readonly authenticationProvider: AuthenticationProvider,
  ) {}

  async login(request: LoginRequest): Promise<AuthSession> {
    const authenticatedSession =
      await this.authenticationProvider.login(request);

    this.session.set(authenticatedSession);
    this.storeSession(authenticatedSession);

    return authenticatedSession;
  }

  acceptSession(authenticatedSession: AuthSession): void {
    this.session.set(authenticatedSession);
    this.storeSession(authenticatedSession);
  }

  async logout(): Promise<void> {
    const currentSession = this.session();

    try {
      if (currentSession) {
        await this.authenticationProvider.logout();
      }
    } finally {
      this.session.set(null);
      localStorage.removeItem(this.localStorageKey);
    }
  }

  getSession(): AuthSession | null {
    return this.session();
  }

  isAuthenticated(): boolean {
    return this.session() !== null;
  }

  private storeSession(session: AuthSession): void {
    localStorage.setItem(
      this.localStorageKey,
      JSON.stringify(session),
    );
  }

  private loadStoredSession(): AuthSession | null {
    const storedSession = localStorage.getItem(
      this.localStorageKey,
    );

    if (!storedSession) {
      return null;
    }

    try {
      return JSON.parse(storedSession) as AuthSession;
    } catch {
      localStorage.removeItem(this.localStorageKey);
      return null;
    }
  }
}
