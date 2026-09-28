/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: foreign-key-dialog.component.ts
 * Purpose: Foreign-key authoring dialog for Model Studio.
 *
 * FORGE AI proposes a foreign-key mapping. The user reviews and applies the
 * proposal to the manual form. Saving is handled by the parent through the
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
  ForgeForeignKey,
  ForgeSpecificationEntity,
} from '../../../../core/interfaces/forge-specification.interface';
import {
  AIForeignKeyProposalResponse,
} from '../../../../core/interfaces/ai-foreign-key-proposal.interface';
import { AIService } from '../../../../core/services/ai.service';

import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';
import { ChoiceDividerComponent } from '../../../../shared/components/choice-divider/choice-divider.component';
import { AiAssistPanelComponent } from '../../../../shared/components/ai-assist-panel/ai-assist-panel.component';

export interface ForeignKeyDraft {
  sourceEntity: string;
  sourceFields: string[];
  targetEntity: string;
}

@Component({
  selector: 'app-model-studio-foreign-key-dialog',
  standalone: true,
  imports: [
    FormDialogComponent,
    ChoiceDividerComponent,
    AiAssistPanelComponent,
  ],
  templateUrl: './foreign-key-dialog.component.html',
  styleUrl: './foreign-key-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ForeignKeyDialogComponent {
  readonly entities = input<ForgeSpecificationEntity[]>([]);
  readonly foreignKeys = input<ForgeForeignKey[]>([]);
  readonly sourceEntityContext = input('');

  readonly saved = output<ForeignKeyDraft>();
  readonly closed = output<void>();

  private readonly aiService = inject(AIService);

  readonly aiPrompt = signal('');
  readonly aiGenerating = signal(false);
  readonly aiResponse =
    signal<AIForeignKeyProposalResponse | null>(null);

  readonly aiCapability = signal<{
    available: boolean;
    model?: string | null;
    mode?: string | null;
  } | null>(null);

  readonly aiExamples = [
    {
      label: 'Single-field reference',
      prompt:
        'Make CUSTOMER_ID on SALES_ORDER reference the identity of CUSTOMER.',
    },
    {
      label: 'Composite reference',
      prompt:
        'Make PRODUCT_ID and PLANT_ID on INVENTORY reference the composite identity of PRODUCT_PLANT.',
    },
    {
      label: 'Child-to-parent reference',
      prompt:
        'Make SALES_ORDER_LINE reference SALES_ORDER using the matching identity fields.',
    },
  ];

  readonly sourceEntity = signal('');
  readonly targetEntity = signal('');

  readonly sourceEntityData = computed(() =>
    this.entities().find(
      (entity) => entity.name === this.sourceEntity(),
    ) ?? null,
  );

  readonly targetEntityData = computed(() =>
    this.entities().find(
      (entity) => entity.name === this.targetEntity(),
    ) ?? null,
  );

  readonly targetIdentityFields = computed(
    () => this.targetEntityData()?.identity?.fields ?? [],
  );

  readonly targetIdentityCount = computed(
    () => this.targetIdentityFields().length,
  );

  readonly sourceFields = computed(() => {
    const sourceFields = this.sourceEntityData()?.fields ?? [];
    const targetIdentity = this.targetIdentityFields();

    return targetIdentity
      .map((targetField) =>
        sourceFields.find((sourceField) => sourceField.name === targetField),
      )
      .filter(
        (
          field,
        ): field is NonNullable<typeof field> => field !== undefined,
      );
  });

  readonly missingSourceFields = computed(() => {
    const sourceFields = this.sourceEntityData()?.fields ?? [];
    const targetIdentity = this.targetIdentityFields();

    return targetIdentity.filter(
      (targetField) =>
        !sourceFields.some(
          (sourceField) => sourceField.name === targetField,
        ),
    );
  });

  readonly hasTargetIdentity = computed(
    () => this.targetIdentityFields().length > 0,
  );

  readonly hasCompleteSourceMapping = computed(
    () =>
      this.hasTargetIdentity() &&
      this.missingSourceFields().length === 0,
  );

  readonly duplicateForeignKey = computed(() => {
    const source = this.sourceEntity();
    const sourceFields = this.sourceFields().map(
      (field) => field.name,
    );
    const target = this.targetEntity();

    return this.foreignKeys().some(
      (foreignKey) =>
        foreignKey.source.entity === source &&
        foreignKey.target.entity === target &&
        this.sameFields(
          foreignKey.source.fields,
          sourceFields,
        ),
    );
  });

  readonly canSave = computed(
    () =>
      this.sourceEntity().trim().length > 0 &&
      this.targetEntity().trim().length > 0 &&
      this.sourceEntity() !== this.targetEntity() &&
      this.hasTargetIdentity() &&
      this.hasCompleteSourceMapping() &&
      !this.duplicateForeignKey(),
  );

  readonly validationMessage = computed(() => {
    if (!this.sourceEntity() || !this.targetEntity()) {
      return '';
    }

    if (this.sourceEntity() === this.targetEntity()) {
      return 'Source and target entities must be different.';
    }

    if (!this.hasTargetIdentity()) {
      return `Target entity ${this.targetEntity()} must define an identity before it can be referenced by a foreign key.`;
    }

    const missingFields = this.missingSourceFields();

    if (missingFields.length > 0) {
      return `${this.sourceEntity()} does not contain the required source field${missingFields.length === 1 ? '' : 's'} ${missingFields.join(', ')} to reference the identity of ${this.targetEntity()}.`;
    }

    if (this.duplicateForeignKey()) {
      return 'This foreign key already exists.';
    }

    return '';
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

  constructor() {
    this.loadAiCapability();

    effect(() => {
      const sourceContext = this.sourceEntityContext();

      if (sourceContext && this.sourceEntity() !== sourceContext) {
        this.sourceEntity.set(sourceContext);
      }
    });
  }

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
      .proposeForeignKey({
        mode: 'CREATE',
        entities: this.entities().map((entity) => ({
          name: entity.name,
          fields: entity.fields.map((field) => ({
            name: field.name,
            type: field.type,
          })),
          identity_fields: entity.identity?.fields ?? [],
        })),
        request,
        existingForeignKey: null,
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
              'FORGE AI could not generate a foreign key proposal right now.',
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

    this.sourceEntity.set(proposal.sourceEntity);
    this.targetEntity.set(proposal.targetEntity);

    this.aiResponse.set(null);
  }

  selectSourceEntity(entityName: string): void {
    this.sourceEntity.set(entityName);
  }

  selectTargetEntity(entityName: string): void {
    this.targetEntity.set(entityName);
  }

  save(): void {
    if (!this.canSave()) {
      return;
    }

    this.saved.emit({
      sourceEntity: this.sourceEntity(),
      sourceFields: this.sourceFields().map(
        (field) => field.name,
      ),
      targetEntity: this.targetEntity(),
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

  private sameFields(left: string[], right: string[]): boolean {
    return (
      left.length === right.length &&
      left.every((field, index) => field === right[index])
    );
  }
}
