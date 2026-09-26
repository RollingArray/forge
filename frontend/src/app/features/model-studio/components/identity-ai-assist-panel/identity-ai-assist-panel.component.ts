import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input,
  output,
  signal,
} from '@angular/core';

import { AICapability } from '../../../../core/interfaces/ai-capability.interface';
import { AIIdentityProposal } from '../../../../core/interfaces/ai-identity-proposal.interface';
import { AIService } from '../../../../core/services/ai.service';

@Component({
  selector: 'app-identity-ai-assist-panel',
  standalone: true,
  templateUrl: './identity-ai-assist-panel.component.html',
  styleUrl: './identity-ai-assist-panel.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IdentityAiAssistPanelComponent {
  private readonly aiService = inject(AIService);

  readonly generating = input(false);
  readonly proposal = input<AIIdentityProposal | null>(null);
  readonly status = input<'PROPOSE' | 'CLARIFY' | 'UNSUPPORTED' | null>(null);
  readonly message = input('');
  readonly error = input('');
  readonly prompt = input('');

  readonly generate = output<string>();
  readonly regenerate = output<void>();
  readonly useProposal = output<void>();
  readonly promptChange = output<string>();

  readonly capability = signal<AICapability | null>(null);
  readonly capabilityLoading = signal(true);

  readonly examples = [
    {
      label: 'Single-field identity',
      prompt: 'Use <field_1> as the unique identity for this entity.',
    },
    {
      label: 'Composite identity',
      prompt: 'Use <field_1> and <field_2> as the identity for this entity.',
    },
    {
      label: 'Existing business key',
      prompt: 'Use <field_1> as the unique identity for this entity.',
    },
  ];

  constructor() {
    this.loadCapabilities();
  }

  loadCapabilities(): void {
    this.capabilityLoading.set(true);

    this.aiService.getCapabilities().subscribe({
      next: (capability) => {
        this.capability.set(capability);
        this.capabilityLoading.set(false);
      },
      error: () => {
        this.capability.set({
          available: false,
          provider: '',
          mode: '',
          model: null,
          message: 'FORGE AI is currently unavailable.',
        });
        this.capabilityLoading.set(false);
      },
    });
  }

  selectExample(prompt: string): void {
    this.promptChange.emit(prompt);
  }

  submit(): void {
    const value = this.prompt().trim();

    if (!value || this.generating() || !this.capability()?.available) {
      return;
    }

    this.generate.emit(value);
  }

  typeChanged(event: Event): void {
    const input = event.target as HTMLTextAreaElement;
    this.promptChange.emit(input.value);
  }
}
