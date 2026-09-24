import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';

import { StudioStep } from '../../screens/model-studio/models/model-studio.models';

@Injectable({
  providedIn: 'root',
})
export class ForgeNavigationService {
  private readonly router = inject(Router);

  private readonly routes: Partial<Record<StudioStep, string>> = {
    model: '/model-studio',
    validate: '/validate',
    population: '/population-plan',
    generate: '/generate',
    results: '/results',
  };

  navigateToStep(step: StudioStep): void {
    const route = this.routes[step];

    if (!route) {
      console.info(
        `[FORGE Navigation] Route not implemented for workflow step: ${step}`,
      );
      return;
    }

    void this.router.navigate([route]);
  }

  navigateToHome(): void {
    void this.router.navigate(['/home']);
  }

  navigateToLogin(): void {
    void this.router.navigate(['/login']);
  }
}
