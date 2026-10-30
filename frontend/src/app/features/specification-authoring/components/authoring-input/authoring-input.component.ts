import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
  inject,
  signal,
} from '@angular/core';
import { AIService } from '../../../../core/services/ai.service';
import { AICapability } from '../../../../core/interfaces/ai-capability.interface';
import { AiAssistPanelComponent, AiAssistExample, AiAssistGuide } from '../../../../shared/components/ai-assist-panel/ai-assist-panel.component';

@Component({
  selector: 'app-authoring-input',
  standalone: true,
  imports: [AiAssistPanelComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './authoring-input.component.html',
  styleUrl: './authoring-input.component.css',
})
export class AuthoringInputComponent {
  private readonly aiService = inject(AIService);

  readonly aiCapability = signal<AICapability | null>(null);

  readonly guide: AiAssistGuide = {
    title: 'How to describe your model',
    introduction: 'Share what you know about the system. You do not need to know every technical detail.',
    sections: [
      {
        heading: 'Purpose',
        description: 'Explain what the data represents and why it is needed.',
      },
      {
        heading: 'Entities and fields',
        description: 'Name the things represented and the information each record contains.',
      },
      {
        heading: 'Identity',
        description: 'Explain how each record is uniquely identified, including composite keys if known.',
      },
      {
        heading: 'Relationships',
        description: 'Describe how records connect and whether connections are required or optional, if known.',
      },
      {
        heading: 'Business rules',
        description: 'Include required fields, allowed values, numeric limits, uniqueness and hierarchy rules.',
      },
      {
        heading: 'Data volume',
        description: 'Add target record counts and generation requirements when known.',
      },
    ],
    reassurance: 'Write naturally. Unknown details can remain open for clarification; FORGE should not silently invent requirements.',
  };

  readonly guideExpanded = signal(false);

  @Input() orderManagementExample = '';

  get examples(): AiAssistExample[] {
    return [{
      label: 'Order Management',
      description: 'Customers, products, sales orders and order lines, with identities, relationships and requested populations.',
      prompt: this.orderManagementExample,
    }];
  }

  selectExample(prompt: string): void {
    this.guideExpanded.set(false);
    this.exampleSelected.emit(prompt);
  }

  constructor() {
    this.aiService.getCapabilities().subscribe({
      next: (capability) => this.aiCapability.set(capability),
      error: () => this.aiCapability.set(null),
    });
  }

  @Input() prompt = '';
  @Input() generating = false;
  @Input() hasProposal = false;
  @Input() errorMessage: string | null = null;

  @Output() promptChange = new EventEmitter<string>();
  @Output() generate = new EventEmitter<string>();
  @Output() clear = new EventEmitter<void>();
  @Output() exampleSelected = new EventEmitter<string>();
}
