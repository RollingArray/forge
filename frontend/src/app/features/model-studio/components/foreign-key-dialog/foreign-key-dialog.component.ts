import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';

import {
  ForgeSpecificationEntity,
  ForgeForeignKey,
} from '../../../../core/interfaces/forge-specification.interface';

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

  readonly aiExamples = [
    {
      label: 'Single-field reference',
      prompt:
        'Make <source_field> reference the identity of <target_entity>.',
    },
    {
      label: 'Composite reference',
      prompt:
        'Make <source_field_1> and <source_field_2> reference the composite identity of <target_entity>.',
    },
    {
      label: 'Child-to-parent reference',
      prompt:
        '<source_entity> references <target_entity> using the matching identity fields.',
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
    const sourceFields = this.sourceFields().map((field) => field.name);
    const target = this.targetEntity();

    return this.foreignKeys().some(
      (foreignKey) =>
        foreignKey.source.entity === source &&
        foreignKey.target.entity === target &&
        this.sameFields(foreignKey.source.fields, sourceFields),
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

  constructor() {
    effect(() => {
      const sourceContext = this.sourceEntityContext();

      if (sourceContext && this.sourceEntity() !== sourceContext) {
        this.sourceEntity.set(sourceContext);
      }
    });
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
      sourceFields: this.sourceFields().map((field) => field.name),
      targetEntity: this.targetEntity(),
    });
  }

  close(): void {
    this.closed.emit();
  }

  private sameFields(left: string[], right: string[]): boolean {
    return (
      left.length === right.length &&
      left.every((field, index) => field === right[index])
    );
  }
}
