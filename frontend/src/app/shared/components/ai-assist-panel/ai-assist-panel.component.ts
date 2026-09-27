/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: ai-assist-panel.component.ts
 * Purpose: Provides the reusable FORGE AI-assisted interaction shell.
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
  model,
  output,
} from '@angular/core';

import { AIDataModelProposal } from '../../../core/interfaces/ai-data-model-proposal.interface';

export interface AiAssistExample {
  label: string;
  prompt: string;
  example?: string;
}

@Component({
  selector: 'app-ai-assist-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ai-assist-panel.component.html',
  styleUrl: './ai-assist-panel.component.css',
})
export class AiAssistPanelComponent {
  readonly title = input('Start with FORGE AI');

  readonly description = input(
    'Describe what you want to create in natural language. FORGE AI will propose a starting point for you to review.',
  );

  readonly placeholder = input(
    'e.g. I want to model SAP Order-to-Cash including customers, orders, deliveries and invoices.',
  );

  readonly hint = input(
    'Describe the business process, system, or domain.',
  );

  readonly generateLabel = input('Generate with FORGE AI');

  readonly generating = input(false);

  readonly proposal = input<AIDataModelProposal | null>(null);

  readonly llmOnline = input(false);
  readonly llmModel = input<string | null>(null);
  readonly llmMode = input<string | null>(null);

  readonly examples = input<AiAssistExample[]>([]);

  readonly exampleHeading = input('Examples of requests');

  readonly exampleDescription = input(
    'Choose an example to see what you can ask FORGE.',
  );

  readonly decisionTitle = input('AI proposes. You decide.');

  readonly decisionDescription = input(
    "Review the suggestion and apply it when you're ready.",
  );

  readonly prompt = model('');

  readonly generate = output<string>();
  readonly useProposal = output<AIDataModelProposal>();
  readonly regenerate = output<void>();
  readonly exampleSelected = output<string>();

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

  selectExample(prompt: string): void {
    this.prompt.set(prompt);
    this.exampleSelected.emit(prompt);
  }
}
