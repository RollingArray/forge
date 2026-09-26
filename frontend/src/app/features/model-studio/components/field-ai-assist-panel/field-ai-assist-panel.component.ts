import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

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
      prompt: 'Create a unique identifier for aerospace components.',
    },
    {
      label: 'Meaningful text',
      prompt: 'Create a field containing realistic aerospace component descriptions.',
    },
    {
      label: 'Patterned code',
      prompt: 'Create a component code using the pattern COMP-####.',
    },
    {
      label: 'Integer range',
      prompt: 'Create a quantity field with values from 1 to 100.',
    },
    {
      label: 'Decimal range',
      prompt: 'Create a component weight between 0.1 and 500.',
    },
    {
      label: 'Yes / No',
      prompt: 'Create a field indicating whether the component is active.',
    },
    {
      label: 'Category',
      prompt: 'Create a lifecycle status with Active, Retired and Obsolete values.',
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
