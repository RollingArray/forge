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
  OnInit,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ConfirmationDialogComponent } from '../../../../shared/components/confirmation-dialog/confirmation-dialog.component';

import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';
import { AiAssistPanelComponent, AiAssistExample } from '../../../../shared/components/ai-assist-panel/ai-assist-panel.component';
import { AIEntityProposal } from '../../../../core/interfaces/ai-entity-proposal.interface';
import { ForgeSpecificationEntity } from '../../../../core/interfaces/forge-specification-entity.interface';

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
  imports: [FormsModule, FormDialogComponent, AiAssistPanelComponent, ConfirmationDialogComponent],
  templateUrl: './entity-dialog.component.html',
  styleUrl: './entity-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityDialogComponent implements OnInit {
  readonly saved = output<EntityDraft>();
  readonly aiRequested = output<string>();
  readonly entity = input<ForgeSpecificationEntity | null>(null);
  readonly aiLoading = input(false);
  readonly aiError = input<string | null>(null);
  readonly aiProposal = input<AIEntityProposal | null>(null);
  readonly closed = output<void>();
  readonly deleteRequested = output<void>();
  readonly deleteBusy = input(false);
  readonly deleteError = input<string | null>(null);
  readonly deleteConfirmation = signal(false);

  readonly name = signal('');
  readonly description = signal('');
  readonly population = signal<number>(100);

  ngOnInit(): void {
    const entity = this.entity();

    if (entity) {
      this.name.set(entity.name);
      this.description.set(entity.description ?? '');
      this.population.set(entity.population?.count ?? 0);
      this.populationScaling = entity.population?.scaling ?? 'SCALABLE';
    }
  }

  readonly isEditing = () => this.entity() !== null;

  requestDeleteConfirmation(): void {
    if (this.isEditing() && !this.deleteBusy()) {
      this.deleteConfirmation.set(true);
    }
  }

  cancelDeleteConfirmation(): void {
    if (!this.deleteBusy()) {
      this.deleteConfirmation.set(false);
    }
  }

  confirmDelete(): void {
    if (this.isEditing() && !this.deleteBusy()) {
      this.deleteRequested.emit();
    }
  }
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
