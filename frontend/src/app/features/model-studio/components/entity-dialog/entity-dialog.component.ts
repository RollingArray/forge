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
  input,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';
import { AiAssistPanelComponent, AiAssistExample } from '../../../../shared/components/ai-assist-panel/ai-assist-panel.component';
import { AIEntityProposal } from '../../../../core/interfaces/ai-entity-proposal.interface';

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
  imports: [FormsModule, FormDialogComponent, AiAssistPanelComponent],
  templateUrl: './entity-dialog.component.html',
  styleUrl: './entity-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityDialogComponent {
  readonly saved = output<EntityDraft>();
  readonly aiRequested = output<string>();
  readonly aiLoading = input(false);
  readonly aiError = input<string | null>(null);
  readonly aiProposal = input<AIEntityProposal | null>(null);
  readonly closed = output<void>();

  readonly name = signal('');
  readonly description = signal('');
  readonly population = signal<number>(100);
  populationScaling: PopulationScaling = 'SCALABLE';
  readonly aiPrompt = signal('');
  readonly aiExamples: AiAssistExample[] = [
    {
      label: 'Customer master',
      prompt: 'Create a CUSTOMER entity representing enterprise customers with 50,000 records.',
    },
    {
      label: 'SAP customer table',
      prompt: 'Create an SAP customer master table named KNA1 with 100 records.',
    },
    {
      label: 'Sales order header',
      prompt: 'Create a sales order header entity called VBAK with 200 records.',
    },
  ];


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

  applyAiProposal(): void {
    const proposal = this.aiProposal();

    if (!proposal) {
      return;
    }

    this.name.set(proposal.name);
    this.description.set(proposal.description);
    this.population.set(proposal.population);
  }

  requestAiProposal(prompt: string = this.aiPrompt()): void {
    const normalizedPrompt = prompt.trim();

    if (normalizedPrompt && !this.aiLoading()) {
      this.aiPrompt.set(normalizedPrompt);
      this.aiRequested.emit(normalizedPrompt);
    }
  }
}
