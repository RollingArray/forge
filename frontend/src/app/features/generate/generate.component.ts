import {
  ChangeDetectionStrategy,
  Component,
  inject,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  selector: 'app-generate',
  standalone: true,
  templateUrl: './generate.component.html',
  styleUrl: './generate.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerateComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly dataModelId =
    this.route.snapshot.paramMap.get('dataModelId') ?? '';

  backToPopulation(): void {
    if (!this.dataModelId) {
      return;
    }

    this.router.navigate([
      '/workspace',
      this.dataModelId,
      'data-model',
      'population',
    ]);
  }
}
