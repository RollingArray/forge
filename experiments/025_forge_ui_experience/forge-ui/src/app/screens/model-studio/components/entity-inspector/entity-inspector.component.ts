import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  EntityInspectorTabsComponent,
  InspectorTab,
} from '../entity-inspector-tabs/entity-inspector-tabs.component';
import { EntityInspectorRelationshipsComponent } from '../entity-inspector-relationships/entity-inspector-relationships.component';

import { EntityInspectorFieldsComponent } from '../entity-inspector-fields/entity-inspector-fields.component';
import { AskForgeComponent } from '../ask-forge/ask-forge.component';


import {
  CanvasEntity,
  EntityAccent,
  ModelConstraint,
  ModelEntity,
  ModelField,
  ModelRelationship,
} from '../../models/model-studio.models';

@Component({
  selector: 'app-entity-inspector',
  standalone: true,
  imports: [
    EntityInspectorRelationshipsComponent,
    FormsModule,
    EntityInspectorTabsComponent,
    EntityInspectorFieldsComponent,
    AskForgeComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-inspector.component.html',
  styleUrl: './entity-inspector.component.css',
})
export class EntityInspectorComponent {
  readonly entity = input.required<CanvasEntity>();
  readonly entities = input<readonly CanvasEntity[]>([]);
  readonly relationships = input.required<readonly ModelRelationship[]>();
  readonly constraints = input<readonly ModelConstraint[]>([]);

  readonly entityUpdated = output<{
    entityName: string;
    description: string;
    accent: EntityAccent;
  }>();

  readonly fieldAdded = output<{
    entityName: string;
    field: ModelField;
  }>();

  readonly relationshipAdded = output<ModelRelationship>();

  readonly constraintAdded = output<ModelConstraint>();

  readonly tab = signal<InspectorTab>('fields');
  readonly editing = signal(false);
  readonly addingField = signal(false);
  readonly addingRelationship = signal(false);
  readonly addingConstraint = signal(false);

  readonly descriptionDraft = signal('');
  readonly accentDraft = signal<EntityAccent>('blue');

  readonly newFieldName = signal('');
  readonly newFieldType = signal('STRING');
  readonly newFieldDescription = signal('');

  readonly newRelationshipEntity = signal('');
  readonly newRelationshipType = signal('ONE_TO_MANY');
  readonly newRelationshipDirection = signal<'forward' | 'reverse'>(
    'forward',
  );
  readonly newRelationshipSourceField = signal('');
  readonly newRelationshipTargetField = signal('');

  readonly newConstraintField = signal('');
  readonly newConstraintOperator = signal('>=');
  readonly newConstraintValue = signal('');

  readonly accents: EntityAccent[] = [
    'blue',
    'green',
    'amber',
    'pink',
    'purple',
  ];

  selectTab(tab: InspectorTab): void {
    this.tab.set(tab);
  }

  startEdit(): void {
    const entity = this.entity();

    this.descriptionDraft.set(entity.description);
    this.accentDraft.set(entity.accent);
    this.editing.set(true);
  }

  cancelEdit(): void {
    this.editing.set(false);
  }

  saveEdit(): void {
    const entity = this.entity();

    this.entityUpdated.emit({
      entityName: entity.name,
      description: this.descriptionDraft(),
      accent: this.accentDraft(),
    });

    this.editing.set(false);
  }

  startAddField(): void {
    this.newFieldName.set('');
    this.newFieldType.set('STRING');
    this.newFieldDescription.set('');
    this.addingField.set(true);
  }

  cancelAddField(): void {
    this.addingField.set(false);
  }

  saveField(): void {
    const name = this.newFieldName().trim();

    if (!name) {
      return;
    }

    this.fieldAdded.emit({
      entityName: this.entity().name,
      field: {
        name,
        type: this.newFieldType(),
        description: this.newFieldDescription().trim(),
      },
    });

    this.addingField.set(false);
  }

  startAddRelationship(): void {
    const available = this.entities().filter(
      entity => entity.name !== this.entity().name,
    );

    this.newRelationshipEntity.set(
      available[0]?.name ?? '',
    );

    this.newRelationshipType.set('ONE_TO_MANY');
    this.newRelationshipDirection.set('forward');

    this.newRelationshipSourceField.set(
      this.entity().fields[0]?.name ?? '',
    );

    this.newRelationshipTargetField.set(
      available[0]?.fields[0]?.name ?? '',
    );

    this.addingRelationship.set(true);
  }

  cancelAddRelationship(): void {
    this.addingRelationship.set(false);
  }

  saveRelationship(): void {
    const relatedEntityName =
      this.newRelationshipEntity();

    if (!relatedEntityName) {
      return;
    }

    const relatedEntity = this.entities().find(
      entity => entity.name === relatedEntityName,
    );

    if (!relatedEntity) {
      return;
    }

    const selectedEntity = this.entity();

    const forward =
      this.newRelationshipDirection() === 'forward';

    const source = forward
      ? selectedEntity
      : relatedEntity;

    const target = forward
      ? relatedEntity
      : selectedEntity;

    const sourceField = forward
      ? this.newRelationshipSourceField()
      : this.newRelationshipTargetField();

    const targetField = forward
      ? this.newRelationshipTargetField()
      : this.newRelationshipSourceField();

    const many =
      this.newRelationshipType() !== 'ONE_TO_ONE';

    this.relationshipAdded.emit({
      source: source.name,
      target: target.name,
      sourceCardinality:
        this.newRelationshipType() === 'MANY_TO_MANY'
          ? 'N'
          : '1',
      targetCardinality:
        this.newRelationshipType() === 'ONE_TO_ONE'
          ? '1'
          : many
            ? 'N'
            : '1',
      sourceParticipation: 'OPTIONAL',
      targetParticipation: 'OPTIONAL',
      type: this.newRelationshipType(),
      sourceFields: sourceField ? [sourceField] : [],
      targetFields: targetField ? [targetField] : [],
    });

    this.addingRelationship.set(false);
  }

  startAddConstraint(): void {
    this.newConstraintField.set(
      this.entity().fields[0]?.name ?? '',
    );
    this.newConstraintOperator.set('>=');
    this.newConstraintValue.set('');
    this.addingConstraint.set(true);
  }

  cancelAddConstraint(): void {
    this.addingConstraint.set(false);
  }

  saveConstraint(): void {
    const field = this.newConstraintField();
    const value = this.newConstraintValue().trim();

    if (!field || !value) {
      return;
    }

    this.constraintAdded.emit({
      id: `user-${Date.now()}`,
      entity: this.entity().name,
      field,
      operator: this.newConstraintOperator(),
      value,
      source: 'user',
    });

    this.addingConstraint.set(false);
  }

  relationshipsForEntity(): ModelRelationship[] {
    const name = this.entity().name;

    return this.relationships().filter(
      relationship =>
        relationship.source === name ||
        relationship.target === name,
    );
  }

  constraintsForEntity(): ModelConstraint[] {
    return this.constraints().filter(
      constraint =>
        constraint.entity === this.entity().name,
    );
  }

  relatedEntityName(
    relationship: ModelRelationship,
  ): string {
    return relationship.source === this.entity().name
      ? relationship.target
      : relationship.source;
  }

  relationshipDirection(
    relationship: ModelRelationship,
  ): string {
    if (relationship.source === this.entity().name) {
      return `${relationship.sourceCardinality} → ${relationship.targetCardinality}`;
    }

    return `${relationship.targetCardinality} → ${relationship.sourceCardinality}`;
  }

  updateRelationshipTarget(): void {
    const entity = this.entities().find(
      candidate =>
        candidate.name === this.newRelationshipEntity(),
    );

    this.newRelationshipTargetField.set(
      entity?.fields[0]?.name ?? '',
    );
  }
}
