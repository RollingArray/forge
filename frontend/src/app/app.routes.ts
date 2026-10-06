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
import { ModelStudioComponent } from './features/model-studio/model-studio.component';
import { ModelValidationComponent } from './features/model-validation/model-validation.component';
import { PopulationComponent } from './features/population/population.component';
import { GenerateComponent } from './features/generate/generate.component';
import { ResultsComponent } from './features/results/results.component';

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
      {
        path: 'workspace/:dataModelId/model-studio',
        component: ModelStudioComponent,
      },
      {
        path: 'workspace/:dataModelId/model-validation',
        component: ModelValidationComponent,
      },
      {
        path: 'workspace/:dataModelId/data-model/population',
        component: PopulationComponent,
      },
      {
        path: 'workspace/:dataModelId/data-model/generate',
        component: GenerateComponent,
      },
      {
        path: 'workspace/:dataModelId/data-model/generate/:jobId',
        component: GenerateComponent,
      },
      {
        path: 'workspace/:dataModelId/data-model/results/:jobId',
        component: ResultsComponent,
      },
    ],
  },
  {
    path: '**',
    redirectTo: 'login',
  },
];
