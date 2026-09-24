/**
 * File: app.routes.ts
 * Purpose: Application route definitions for FORGE.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';
import { AuthenticatedLayoutComponent } from './layout/authenticated/authenticated-layout.component';
import { LoginComponent } from './features/login/login.component';
import { WorkspaceComponent } from './features/workspace/workspace.component';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'login',
  },
  {
    path: 'login',
    component: LoginComponent,
  },
  {
    path: '',
    component: AuthenticatedLayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: 'workspace',
        component: WorkspaceComponent,
      },
    ],
  },
  {
    path: '**',
    redirectTo: 'login',
  },
];
