import { Routes } from '@angular/router';

import { LoginComponent } from './screens/login/login.component';
import { HomeComponent } from './screens/home/home.component';
import { ModelStudioComponent } from './screens/model-studio/model-studio.component';
import { PopulationPlanComponent } from './screens/population-plan/population-plan.component';

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
    path: 'home',
    component: HomeComponent,
  },
  {
    path: 'model-studio',
    component: ModelStudioComponent,
  },
  {
    path: 'population-plan',
    component: PopulationPlanComponent,
  },
  {
    path: '**',
    redirectTo: 'login',
  },
];
