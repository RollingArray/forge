/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: ai-assist-panel.component.ts
 * Purpose: Provides the reusable FORGE AI-assisted form interaction.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  signal,
} from '@angular/core';

import { AIDataModelProposal } from '../../../core/interfaces/ai-data-model-proposal.interface';

@Component({
  selector: 'app-ai-assist-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ai-assist-panel.component.html',
  styleUrl: './ai-assist-panel.component.css',
})
export class AiAssistPanelComponent {
  readonly title = input('Describe what you want to create');
  readonly description = input(
    'Describe your intent in natural language and let FORGE AI propose a starting point.',
  );
  readonly placeholder = input(
    'e.g. I want to model SAP Order-to-Cash including customers, orders, deliveries and invoices.',
  );
  readonly generateLabel = input('Generate with FORGE AI');
  readonly generating = input(false);
  readonly proposal = input<AIDataModelProposal | null>(null);

  readonly llmOnline = input(false);
  readonly llmModel = input<string | null>(null);
  readonly llmMode = input<string | null>(null);

  readonly prompt = signal('');

  readonly generate = output<string>();
  readonly useProposal = output<AIDataModelProposal>();
  readonly regenerate = output<void>();

  applyProposal(): void {
    const proposal = this.proposal();

    if (proposal) {
      this.useProposal.emit(proposal);
    }
  }

  regenerateProposal(): void {
    this.regenerate.emit();
  }

  generateSuggestion(): void {
    const prompt = this.prompt().trim();

    if (!prompt || this.generating()) {
      return;
    }

    this.generate.emit(prompt);
  }
}
