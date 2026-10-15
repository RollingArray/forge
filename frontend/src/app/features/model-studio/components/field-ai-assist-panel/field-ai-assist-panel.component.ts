import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { AIFieldProposal } from '../../../../core/interfaces/ai-field-proposal.interface';

@Component({
  selector: 'app-field-ai-assist-panel',
  standalone: true,
  templateUrl: './field-ai-assist-panel.component.html',
  styleUrl: './field-ai-assist-panel.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FieldAiAssistPanelComponent {
  readonly generating = input(false);
  readonly proposal = input<AIFieldProposal | null>(null);
  readonly status = input<'PROPOSE' | 'CLARIFY' | 'UNSUPPORTED' | null>(null);
  readonly message = input('');
  readonly error = input('');
  readonly prompt = input('');

  readonly generate = output<string>();
  readonly regenerate = output<void>();
  readonly useProposal = output<void>();
  readonly promptChange = output<string>();

  readonly examples = [
    {
      label: 'Unique identifier',
      prompt: 'Create a unique identifier for each aerospace component.',
    },
    {
      label: 'Meaningful text',
      prompt: 'Generate realistic descriptions of aerospace components.',
    },
    {
      label: 'Patterned code',
      prompt: 'Create component codes following the pattern COMP-####.',
    },
    {
      label: 'Random string',
      prompt: 'Generate random 12-character alphanumeric codes.',
    },
    {
      label: 'Text with length limits',
      prompt: 'Generate alphanumeric reference strings between 8 and 16 characters.',
    },
    {
      label: 'Whole number range',
      prompt: 'Generate quantities between 1 and 100.',
    },
    {
      label: 'Decimal range',
      prompt: 'Generate component weights between 0.1 and 500.',
    },
    {
      label: 'Normally distributed values',
      prompt: 'Generate measurements centered around 50 using a normal distribution.',
    },
    {
      label: 'Yes / No',
      prompt: 'Create a Boolean field indicating whether a component is active.',
    },
    {
      label: 'Fixed choices',
      prompt: 'Assign lifecycle status from Active, Retired and Obsolete.',
    },
    {
      label: 'Unique meaningful text',
      prompt: 'Generate distinct, realistic descriptions for aerospace components.',
    },
    {
      label: 'Controlled vocabulary',
      prompt: 'Generate material categories using Titanium, Aluminum and Steel.',
    },
    {
      label: 'Bounded measurement',
      prompt: 'Generate operating temperatures between 10 and 150 degrees Celsius.',
    },
    {
      label: 'Narrow numeric range',
      prompt: 'Generate inspection scores between 95 and 100.',
    },
    {
      label: 'Structured reference',
      prompt: 'Generate supplier references following the pattern SUP-AAA-####.',
    },
    {
      label: 'Engineering classification',
      prompt: 'Classify components as Structural, Electrical, Hydraulic or Avionics.',
    },
    {
      label: 'Quality status',
      prompt: 'Assign inspection outcomes from Accepted, Rework and Rejected.',
    },
    {
      label: 'Maintenance interval',
      prompt: 'Generate maintenance intervals between 50 and 5000 operating hours.',
    },
  ];

  selectExample(prompt: string): void {
    this.promptChange.emit(prompt);
  }

  submit(): void {
    const value = this.prompt().trim();

    if (!value || this.generating()) {
      return;
    }

    this.generate.emit(value);
  }

  typeChanged(value: Event): void {
    const input = value.target as HTMLTextAreaElement;
    this.promptChange.emit(input.value);
  }
}
