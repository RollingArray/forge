/**
 * File: app.ts
 * Purpose: Root application component and router outlet host.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ApiLoadingService } from './core/services/api-loading.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  readonly isApiLoading;

  constructor(
    private readonly apiLoadingService: ApiLoadingService,
  ) {
    this.isApiLoading = this.apiLoadingService.isLoading;
  }
}
