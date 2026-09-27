/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: relationship-dialog.component.ts
 * Purpose: Relationship authoring dialog for Model Studio.
 *
 * Relationships are defined between entities. The actual field linkage is
 * resolved from an existing foreign key in the specification.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { AiAssistPanelComponent } from '../../../../shared/components/ai-assist-panel/ai-assist-panel.component';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  inject,
  output,
  signal,
} from '@angular/core';
import { TitleCasePipe } from '@angular/common';

import {
  ForgeForeignKey,
  ForgeSpecificationEntity,
  ForgeSpecificationRelationship,
} from '../../../../core/interfaces/forge-specification.interface';
import { AIService } from '../../../../core/services/ai.service';
import { AICapability } from '../../../../core/interfaces/ai-capability.interface';
import { AIRelationshipProposal } from '../../../../core/interfaces/ai-relationship-proposal.interface';

import { ChoiceDividerComponent } from '../../../../shared/components/choice-divider/choice-divider.component';
import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';

export type RelationshipType =
  | 'ONE_TO_ONE'
  | 'ONE_TO_MANY'
  | 'MANY_TO_ONE'
  | 'MANY_TO_MANY';

export type RelationshipParticipation =
  | 'MANDATORY'
  | 'OPTIONAL';

export interface RelationshipDraft {
  sourceEntity: string;
  targetEntity: string;
  type: RelationshipType;
  sourceParticipation: RelationshipParticipation;
  targetParticipation: RelationshipParticipation;
}

interface RelationshipOption {
  type: RelationshipType;
  label: string;
  description: string;
}


@Component({
  selector: 'app-model-studio-relationship-dialog',
  standalone: true,
  imports: [
    TitleCasePipe,
    FormDialogComponent,
    ChoiceDividerComponent,
    AiAssistPanelComponent,
  ],
  templateUrl: './relationship-dialog.component.html',
  styleUrl: './relationship-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RelationshipDialogComponent {
  readonly entities = input<ForgeSpecificationEntity[]>([]);
  readonly foreignKeys = input<ForgeForeignKey[]>([]);
  readonly sourceEntityContext = input('');
  readonly existingRelationship =
    input<ForgeSpecificationRelationship | null>(null);

  readonly saved = output<RelationshipDraft>();
  readonly closed = output<void>();

  private readonly aiService = inject(AIService);

  readonly sourceEntity = signal('');

  readonly targetEntity = signal('');

  readonly relationshipType =
    signal<RelationshipType>('MANY_TO_ONE');

  readonly sourceParticipation =
    signal<RelationshipParticipation>('MANDATORY');

  readonly targetParticipation =
    signal<RelationshipParticipation>('OPTIONAL');

  readonly aiPrompt = signal('');
  readonly aiGenerating = signal(false);
  readonly aiResponse =
    signal<{
      status: string;
      message: string;
      proposal: AIRelationshipProposal | null;
    } | null>(null);

  readonly aiCapability = signal<AICapability | null>(null);

  readonly relationshipOptions: RelationshipOption[] = [
    {
      type: 'ONE_TO_ONE',
      label: 'One-to-One',
      description: 'One record connects to one record.',
    },
    {
      type: 'ONE_TO_MANY',
      label: 'One-to-Many',
      description: 'One record can connect to many records.',
    },
    {
      type: 'MANY_TO_ONE',
      label: 'Many-to-One',
      description: 'Many records can belong to one record.',
    },
    {
      type: 'MANY_TO_MANY',
      label: 'Many-to-Many',
      description: 'Records can connect to many records.',
    },
  ];

  readonly aiExamples = [
    {
      label: 'One-to-many',
      prompt:
        'Each [child record] belongs to one [parent record], and a [parent record] can have many [child records].',
      example:
        'Each [SalesOrderItem] belongs to one [SalesOrder], and a [SalesOrder] can have many [SalesOrderItems].',
    },
    {
      label: 'Optional relationship',
      prompt:
        'A [parent record] can have many [child records], but a [child record] may exist without a [parent record].',
      example:
        'A [Customer] can have many [SalesOrders], but a [SalesOrder] may exist without a [Customer].',
    },
    {
      label: 'One-to-one',
      prompt:
        'Each [record type A] has one [record type B], and each [record type B] belongs to one [record type A].',
      example:
        'Each [Employee] has one [EmployeeProfile], and each [EmployeeProfile] belongs to one [Employee].',
    },
    {
      label: 'Many-to-many',
      prompt:
        'A [record type A] can be associated with many [record type B], and a [record type B] can be associated with many [record type A].',
      example:
        'A [Student] can be associated with many [Courses], and a [Course] can be associated with many [Students].',
    },
  ];

  readonly resolvedForeignKeys = computed(() => {
    const source = this.sourceEntity();
    const target = this.targetEntity();

    if (!source || !target) {
      return [];
    }

    return this.foreignKeys().filter(
      (foreignKey) =>
        (foreignKey.source.entity === source &&
          foreignKey.target.entity === target) ||
        (foreignKey.source.entity === target &&
          foreignKey.target.entity === source),
    );
  });

  readonly resolvedForeignKey = computed(() => {
    const keys = this.resolvedForeignKeys();

    return keys.length === 1 ? keys[0] : null;
  });

  readonly hasMultipleForeignKeys = computed(
    () => this.resolvedForeignKeys().length > 1,
  );

  readonly canSave = computed(
    () =>
      this.sourceEntity().trim().length > 0 &&
      this.targetEntity().trim().length > 0 &&
      this.sourceEntity() !== this.targetEntity() &&
      this.resolvedForeignKeys().length === 1,
  );

  readonly sourceEntityLabel = computed(
    () => this.sourceEntity() || 'Source entity',
  );

  readonly targetEntityLabel = computed(
    () => this.targetEntity() || 'Target entity',
  );

  readonly relationshipSummary = computed(() => {
    const source = this.sourceEntity();
    const target = this.targetEntity();

    if (!source || !target) {
      return 'Choose the two entities you want to connect.';
    }

    switch (this.relationshipType()) {
      case 'ONE_TO_ONE':
        return `Each ${source} connects to one ${target}, and each ${target} connects to one ${source}.`;

      case 'ONE_TO_MANY':
        return `Each ${source} can connect to many ${target} records.`;

      case 'MANY_TO_ONE':
        return `Many ${source} records can belong to one ${target}.`;

      case 'MANY_TO_MANY':
        return `${source} and ${target} records can connect to many records on the other side.`;
    }
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

  constructor() {
    effect(() => {
      const contextualEntity = this.sourceEntityContext();

      if (contextualEntity && !this.existingRelationship()) {
        this.sourceEntity.set(contextualEntity);
      }
    });

    effect(() => {
      const existing = this.existingRelationship();

      if (!existing) {
        return;
      }

      const source = this.parseEntity(existing.source);
      const target = this.parseEntity(existing.target);

      if (source) {
        this.sourceEntity.set(source);
      }

      if (target) {
        this.targetEntity.set(target);
      }

      this.relationshipType.set(
        existing.type as RelationshipType,
      );

      this.sourceParticipation.set(
        (existing.source_participation ??
          'MANDATORY') as RelationshipParticipation,
      );

      this.targetParticipation.set(
        (existing.target_participation ??
          'MANDATORY') as RelationshipParticipation,
      );
    });

    this.loadAiCapability();
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
      .proposeRelationship({
        mode: this.existingRelationship() ? 'EDIT' : 'CREATE',
        entities: this.entities().map((entity) => ({
          name: entity.name,
          fields: entity.fields.map((field) => ({
            name: field.name,
            type: field.type,
          })),
          identity_fields: entity.identity?.fields ?? [],
        })),
        request,
        existingRelationship: this.existingRelationship()
          ? {
              source: this.existingRelationship()!.source,
              target: this.existingRelationship()!.target,
              type: this.existingRelationship()!.type,
              source_participation:
                this.existingRelationship()!.source_participation,
              target_participation:
                this.existingRelationship()!.target_participation,
            }
          : null,
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
              'FORGE AI could not generate a relationship proposal right now.',
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
    this.relationshipType.set(proposal.type);
    this.sourceParticipation.set(proposal.sourceParticipation);
    this.targetParticipation.set(proposal.targetParticipation);

    this.aiResponse.set(null);
  }

  selectSourceEntity(entityName: string): void {
    this.sourceEntity.set(entityName);
  }

  selectTargetEntity(entityName: string): void {
    this.targetEntity.set(entityName);
  }

  selectRelationshipType(type: RelationshipType): void {
    this.relationshipType.set(type);
  }

  setSourceParticipation(
    participation: RelationshipParticipation,
  ): void {
    this.sourceParticipation.set(participation);
  }

  setTargetParticipation(
    participation: RelationshipParticipation,
  ): void {
    this.targetParticipation.set(participation);
  }

  save(): void {
    if (!this.canSave()) {
      return;
    }

    this.saved.emit({
      sourceEntity: this.sourceEntity(),
      targetEntity: this.targetEntity(),
      type: this.relationshipType(),
      sourceParticipation: this.sourceParticipation(),
      targetParticipation: this.targetParticipation(),
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

  private parseEntity(endpoint: string): string | null {
    const separator = endpoint.indexOf('.');

    if (separator <= 0) {
      return null;
    }

    return endpoint.slice(0, separator);
  }
}
