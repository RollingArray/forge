/**
 * File: entity-dialog.component.ts
 * Purpose: Add Entity authoring dialog for Model Studio.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import {
  ChangeDetectionStrategy,
  Component,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';

export type PopulationScaling = 'FIXED' | 'SCALABLE';

export interface EntityDraft {
  name: string;
  description: string;
  population: number;
  scaling: PopulationScaling;
}

@Component({
  selector: 'app-model-studio-entity-dialog',
  standalone: true,
  imports: [FormsModule, FormDialogComponent],
  templateUrl: './entity-dialog.component.html',
  styleUrl: './entity-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityDialogComponent {
  readonly saved = output<EntityDraft>();
  readonly aiRequested = output<string>();
  readonly closed = output<void>();

  readonly name = signal('');
  readonly description = signal('');
  readonly population = signal<number>(100);
  populationScaling: PopulationScaling = 'SCALABLE';
  readonly aiPrompt = signal('');

  canSave(): boolean {
    return (
      this.name().trim().length > 0 &&
      Number.isInteger(this.population()) &&
      this.population() >= 0
    );
  }

  save(): void {
    if (!this.canSave()) {
      return;
    }

    this.saved.emit({
      name: this.name().trim(),
      description: this.description().trim(),
      population: this.population(),
      scaling: this.populationScaling,
    });
  }

  useExample(prompt: string): void {
    this.aiPrompt.set(prompt);
  }

  requestAiProposal(): void {
    const prompt = this.aiPrompt().trim();

    if (prompt) {
      this.aiRequested.emit(prompt);
    }
  }
}
