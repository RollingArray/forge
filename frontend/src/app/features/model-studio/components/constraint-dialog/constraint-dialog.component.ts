/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: constraint-dialog.component.ts
 * Purpose: Constraint authoring dialog for Model Studio.
 *
 * FORGE AI proposes a constraint. The user reviews and applies the proposal
 * to the manual form. Saving is handled by the parent through the
 * deterministic SpecificationService.
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';

import {
  ForgeConstraint,
  ForgeSpecificationEntity,
} from '../../../../core/interfaces/forge-specification.interface';
import { AIConstraintProposalResponse } from '../../../../core/interfaces/ai-constraint-proposal.interface';
import { AIService } from '../../../../core/services/ai.service';

import { AiAssistPanelComponent } from '../../../../shared/components/ai-assist-panel/ai-assist-panel.component';
import { ChoiceCardComponent } from '../../../../shared/components/choice-card/choice-card.component';
import { ChoiceDividerComponent } from '../../../../shared/components/choice-divider/choice-divider.component';
import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';

export type ConstraintOperator =
  | '>'
  | '>='
  | '<'
  | '<='
  | '=='
  | '!=';

export interface ConstraintDraft {
  entity: string;
  field: string;
  operator: ConstraintOperator;
  value: string | number | boolean;
}

interface ConstraintOperatorOption {
  operator: ConstraintOperator;
  label: string;
  description: string;
}

@Component({
  selector: 'app-model-studio-constraint-dialog',
  standalone: true,
  imports: [
    FormDialogComponent,
    ChoiceDividerComponent,
    ChoiceCardComponent,
    AiAssistPanelComponent,
  ],
  templateUrl: './constraint-dialog.component.html',
  styleUrl: './constraint-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConstraintDialogComponent {
  readonly entity = input.required<ForgeSpecificationEntity>();

  readonly existingConstraint =
    input<ForgeConstraint | null>(null);

  readonly saved = output<ConstraintDraft>();
  readonly closed = output<void>();

  private readonly aiService = inject(AIService);

  readonly field = signal('');
  readonly operator = signal<ConstraintOperator>('>=');
  readonly value = signal('');

  readonly aiPrompt = signal('');
  readonly aiGenerating = signal(false);
  readonly aiResponse =
    signal<AIConstraintProposalResponse | null>(null);

  readonly aiCapability = signal<{
    available: boolean;
    model?: string | null;
    mode?: string | null;
  } | null>(null);

  readonly operatorOptions: readonly ConstraintOperatorOption[] = [
    {
      operator: '>',
      label: 'Greater than',
      description: 'Value must be greater than the comparison value.',
    },
    {
      operator: '>=',
      label: 'Greater than or equal',
      description: 'Value must be greater than or equal to the comparison value.',
    },
    {
      operator: '<',
      label: 'Less than',
      description: 'Value must be less than the comparison value.',
    },
    {
      operator: '<=',
      label: 'Less than or equal',
      description: 'Value must be less than or equal to the comparison value.',
    },
    {
      operator: '==',
      label: 'Equal to',
      description: 'Value must equal the comparison value.',
    },
    {
      operator: '!=',
      label: 'Not equal to',
      description: 'Value must not equal the comparison value.',
    },
  ];

  private readonly supportedOperatorsByFieldType: Readonly<
    Record<string, readonly ConstraintOperator[]>
  > = {
    INTEGER: ['>', '>=', '<', '<='],
    DECIMAL: ['>', '>=', '<', '<='],
    CATEGORICAL: ['==', '!='],
  };

  readonly selectedField = computed(() =>
    this.entity().fields.find(
      (field) => field.name === this.field(),
    ),
  );

  readonly availableOperatorOptions = computed(() => {
    const fieldType = this.selectedField()?.type;

    if (!fieldType) {
      return [];
    }

    const supportedOperators =
      this.supportedOperatorsByFieldType[fieldType] ?? [];

    return this.operatorOptions.filter(
      (option) => supportedOperators.includes(option.operator),
    );
  });

  readonly constraintsSupported = computed(
    () => this.availableOperatorOptions().length > 0,
  );

  readonly categoricalValues = computed(() => {
    const field = this.selectedField();

    if (
      !field ||
      field.type !== 'CATEGORICAL' ||
      field.generation?.distribution !== 'CATEGORICAL'
    ) {
      return [];
    }

    const values = field.generation.parameters?.['values'];

    return Array.isArray(values)
      ? values.filter(
          (value): value is string | number | boolean =>
            typeof value === 'string' ||
            typeof value === 'number' ||
            typeof value === 'boolean',
        )
      : [];
  });

  readonly categoricalVocabularyAvailable = computed(
    () => this.categoricalValues().length > 0,
  );

  readonly aiExamples = [
    {
      label: 'Minimum age',
      prompt: 'Customer AGE must be greater than or equal to 18.',
      example: 'Customer AGE must be greater than or equal to 18.',
    },
    {
      label: 'Positive quantity',
      prompt: 'Quantity must be greater than 0.',
      example: 'Quantity must be greater than 0.',
    },
    {
      label: 'Maximum value',
      prompt: 'Weight must be less than or equal to 500.',
      example: 'Weight must be less than or equal to 500.',
    },
    {
      label: 'Status value',
      prompt: 'Status must equal ACTIVE.',
      example: 'Status must equal ACTIVE.',
    },
  ];

  readonly canSave = computed(() => {
    if (
      !this.field().trim() ||
      !this.value().trim() ||
      !this.constraintsSupported()
    ) {
      return false;
    }

    if (this.selectedField()?.type === 'CATEGORICAL') {
      return this.categoricalVocabularyAvailable() &&
        this.categoricalValues().some(
          (candidate) => String(candidate) === this.value(),
        );
    }

    return true;
  });

  readonly aiOnline = computed(
    () => this.aiCapability()?.available ?? false,
  );

  readonly aiModel = computed(
    () => this.aiCapability()?.model ?? null,
  );

  readonly aiMode = computed(
    () => this.aiCapability()?.mode ?? null,
  );

  handleAiGenerate(prompt: string): void {
    this.aiPrompt.set(prompt);
    this.generateWithAi();
  }

  selectAiExample(prompt: string): void {
    this.aiPrompt.set(prompt);
    this.aiResponse.set(null);
  }

  generateWithAi(): void {
    const request = this.aiPrompt().trim();

    if (!request || this.aiGenerating()) {
      return;
    }

    this.aiGenerating.set(true);
    this.aiResponse.set(null);

    this.aiService
      .proposeConstraint({
        mode: 'CREATE',
        entities: [
          {
            name: this.entity().name,
            fields: this.entity().fields.map((field) => ({
              name: field.name,
              type: field.type,
            })),
            identity_fields: this.entity().identity?.fields ?? [],
          },
        ],
        request,
        existingConstraint: null,
      })
      .subscribe({
        next: (response) => {
          this.aiResponse.set(response);
          this.aiGenerating.set(false);
        },
        error: (error) => {
          this.aiResponse.set({
            status: 'UNSUPPORTED',
            message:
              error?.error?.detail ??
              'FORGE AI could not generate a constraint proposal right now.',
            proposal: null,
          });
          this.aiGenerating.set(false);
        },
      });
  }

  regenerateAi(): void {
    this.generateWithAi();
  }

  applyAiProposal(): void {
    const proposal = this.aiResponse()?.proposal;

    if (!proposal) {
      return;
    }

    this.field.set(proposal.field);
    this.operator.set(proposal.operator);
    this.value.set(String(proposal.value));

    this.aiResponse.set(null);
  }

  selectField(fieldName: string): void {
    this.field.set(fieldName);
    this.value.set('');

    const supportedOperators = this.availableOperatorOptions();

    if (
      supportedOperators.length > 0 &&
      !supportedOperators.some(
        (option) => option.operator === this.operator(),
      )
    ) {
      this.operator.set(supportedOperators[0].operator);
    }
  }

  selectOperator(operator: ConstraintOperator): void {
    if (
      !this.availableOperatorOptions().some(
        (option) => option.operator === operator,
      )
    ) {
      return;
    }

    this.operator.set(operator);
  }

  setValue(value: string): void {
    this.value.set(value);
  }

  selectCategoricalValue(value: string | number | boolean): void {
    this.value.set(String(value));
  }

  categoricalValueAsString(
    value: string | number | boolean,
  ): string {
    return String(value);
  }

  save(): void {
    if (!this.canSave()) {
      return;
    }

    this.saved.emit({
      entity: this.entity().name,
      field: this.field(),
      operator: this.operator(),
      value: this.value(),
    });
  }

  close(): void {
    this.closed.emit();
  }

  private loadAiCapability(): void {
    this.aiService.getCapabilities().subscribe({
      next: (capability) => {
        this.aiCapability.set(capability);
      },
      error: () => {
        this.aiCapability.set(null);
      },
    });
  }

  constructor() {
    this.loadAiCapability();

    effect(() => {
      const existingConstraint = this.existingConstraint();

      if (!existingConstraint) {
        return;
      }

      this.field.set(existingConstraint.field);
      this.operator.set(
        existingConstraint.operator as ConstraintOperator,
      );
      this.value.set(String(existingConstraint.value));
    });
  }
}
