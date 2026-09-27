import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';

import {
  ForgeSpecificationEntity,
  ForgeSpecificationRelationship,
} from '../../../../core/interfaces/forge-specification.interface';
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
  sourceField: string;
  targetEntity: string;
  targetField: string;
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
    FormDialogComponent,
    ChoiceDividerComponent,
  ],
  templateUrl: './relationship-dialog.component.html',
  styleUrl: './relationship-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RelationshipDialogComponent {
  readonly entities =
    input.required<ForgeSpecificationEntity[]>();

  readonly existingRelationship =
    input<ForgeSpecificationRelationship | null>(null);

  readonly closed = output<void>();
  readonly saved = output<RelationshipDraft>();

  readonly sourceEntity = signal('');
  readonly sourceField = signal('');
  readonly targetEntity = signal('');
  readonly targetField = signal('');

  readonly relationshipType =
    signal<RelationshipType>('MANY_TO_ONE');

  readonly sourceParticipation =
    signal<RelationshipParticipation>('MANDATORY');

  readonly targetParticipation =
    signal<RelationshipParticipation>('OPTIONAL');

  readonly relationshipOptions: readonly RelationshipOption[] = [
    {
      type: 'ONE_TO_ONE',
      label: 'Each record connects to one record',
      description:
        'One record on either side can connect to only one record on the other side.',
    },
    {
      type: 'ONE_TO_MANY',
      label: 'One record can connect to many records',
      description:
        'A single source record can connect to multiple target records.',
    },
    {
      type: 'MANY_TO_ONE',
      label: 'Many records can belong to one record',
      description:
        'Multiple source records can connect to the same target record.',
    },
    {
      type: 'MANY_TO_MANY',
      label: 'Records can connect to many records',
      description:
        'Records on both sides can connect to multiple records.',
    },
  ];

  readonly sourceFields = computed(() =>
    this.fieldsFor(this.sourceEntity()),
  );

  readonly targetFields = computed(() =>
    this.fieldsFor(this.targetEntity()),
  );

  readonly canSave = computed(
    () =>
      this.sourceEntity().trim().length > 0 &&
      this.sourceField().trim().length > 0 &&
      this.targetEntity().trim().length > 0 &&
      this.targetField().trim().length > 0 &&
      this.sourceEntity() !== this.targetEntity(),
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

  constructor() {
    const existing = this.existingRelationship();

    if (existing) {
      const source = this.parseEndpoint(existing.source);
      const target = this.parseEndpoint(existing.target);

      if (source) {
        this.sourceEntity.set(source.entity);
        this.sourceField.set(source.field);
      }

      if (target) {
        this.targetEntity.set(target.entity);
        this.targetField.set(target.field);
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
    }
  }

  selectSourceEntity(entityName: string): void {
    this.sourceEntity.set(entityName);
    this.sourceField.set('');
  }

  selectTargetEntity(entityName: string): void {
    this.targetEntity.set(entityName);
    this.targetField.set('');
  }

  selectSourceField(fieldName: string): void {
    this.sourceField.set(fieldName);
  }

  selectTargetField(fieldName: string): void {
    this.targetField.set(fieldName);
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
      sourceField: this.sourceField(),
      targetEntity: this.targetEntity(),
      targetField: this.targetField(),
      type: this.relationshipType(),
      sourceParticipation: this.sourceParticipation(),
      targetParticipation: this.targetParticipation(),
    });
  }

  close(): void {
    this.closed.emit();
  }

  private fieldsFor(
    entityName: string,
  ): ForgeSpecificationEntity['fields'] {
    return (
      this.entities().find(
        (entity) => entity.name === entityName,
      )?.fields ?? []
    );
  }

  private parseEndpoint(
    endpoint: string,
  ): { entity: string; field: string } | null {
    const separator = endpoint.indexOf('.');

    if (separator <= 0 || separator === endpoint.length - 1) {
      return null;
    }

    return {
      entity: endpoint.slice(0, separator),
      field: endpoint.slice(separator + 1),
    };
  }
}
