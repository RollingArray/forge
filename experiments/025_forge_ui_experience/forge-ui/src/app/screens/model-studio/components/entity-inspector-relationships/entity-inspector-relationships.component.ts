import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';

import {
  CanvasEntity,
  ModelRelationship,
} from '../../models/model-studio.models';

@Component({
  selector: 'app-entity-inspector-relationships',
  standalone: true,
  templateUrl: './entity-inspector-relationships.component.html',
  styleUrl: './entity-inspector-relationships.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityInspectorRelationshipsComponent {
  readonly entity = input.required<CanvasEntity>();
  readonly entities = input<readonly CanvasEntity[]>([]);
  readonly relationships = input<readonly ModelRelationship[]>([]);

  readonly relationshipAdded = output<ModelRelationship>();
  readonly relationshipEdit = output<ModelRelationship>();
  readonly relationshipDelete = output<ModelRelationship>();

  readonly openMenuIndex = signal<number | null>(null);
  readonly adding = signal(false);

  readonly newEntity = signal('');
  readonly newType = signal('ONE_TO_MANY');
  readonly newDirection = signal<'OUTGOING' | 'INCOMING'>('OUTGOING');
  readonly newSourceField = signal('');
  readonly newTargetField = signal('');

  readonly selectedRelationships = computed(() =>
    this.relationships().filter(
      relationship =>
        relationship.source === this.entity().name ||
        relationship.target === this.entity().name,
    ),
  );

  readonly availableEntities = computed(() =>
    this.entities().filter(item => item.name !== this.entity().name),
  );

  sourceEntity(relationship: ModelRelationship): CanvasEntity | undefined {
    return this.entities().find(item => item.name === relationship.source);
  }

  targetEntity(relationship: ModelRelationship): CanvasEntity | undefined {
    return this.entities().find(item => item.name === relationship.target);
  }

  sourceFields(relationship: ModelRelationship): string[] {
    return relationship.sourceFields ?? [];
  }

  targetFields(relationship: ModelRelationship): string[] {
    return relationship.targetFields ?? [];
  }

  sourceParticipation(relationship: ModelRelationship): string {
    return relationship.sourceParticipation ?? 'OPTIONAL';
  }

  targetParticipation(relationship: ModelRelationship): string {
    return relationship.targetParticipation ?? 'OPTIONAL';
  }

  participationClass(value: string): string {
    return value === 'MANDATORY' ? 'mandatory' : 'optional';
  }

  cardinality(relationship: ModelRelationship): string {
    return `${relationship.sourceCardinality}..${relationship.targetCardinality}`;
  }

  cardinalityDescription(relationship: ModelRelationship): string {
    const value = this.cardinality(relationship);

    switch (value) {
      case '1..1':
        return 'One to one';
      case '1..N':
        return 'One to many';
      case 'N..1':
        return 'Many to one';
      case 'N..N':
        return 'Many to many';
      default:
        return '';
    }
  }

  accentClass(entity?: CanvasEntity): string {
    return entity?.accent ?? 'blue';
  }

  toggleMenu(index: number): void {
    this.openMenuIndex.update(current =>
      current === index ? null : index,
    );
  }

  editRelationship(relationship: ModelRelationship): void {
    this.openMenuIndex.set(null);
    this.relationshipEdit.emit(relationship);
  }

  deleteRelationship(relationship: ModelRelationship): void {
    this.openMenuIndex.set(null);
    this.relationshipDelete.emit(relationship);
  }

  startAdd(): void {
    const firstEntity = this.availableEntities()[0];

    this.newEntity.set(firstEntity?.name ?? '');
    this.newType.set('ONE_TO_MANY');
    this.newDirection.set('OUTGOING');
    this.newSourceField.set('');
    this.newTargetField.set('');
    this.adding.set(true);
  }

  cancelAdd(): void {
    this.adding.set(false);
  }

  saveRelationship(): void {
    const relatedEntity = this.entities().find(
      item => item.name === this.newEntity(),
    );

    if (!relatedEntity) {
      return;
    }

    const forward = this.newDirection() === 'OUTGOING';

    const source = forward ? this.entity() : relatedEntity;
    const target = forward ? relatedEntity : this.entity();

    const sourceField = forward
      ? this.newSourceField()
      : this.newTargetField();

    const targetField = forward
      ? this.newTargetField()
      : this.newSourceField();

    const [sourceCardinality, targetCardinality] =
      this.cardinalitiesForType(this.newType());

    this.relationshipAdded.emit({
      source: source.name,
      target: target.name,
      sourceCardinality,
      targetCardinality,
      sourceParticipation: 'OPTIONAL',
      targetParticipation: 'OPTIONAL',
      type: this.newType(),
      sourceFields: sourceField ? [sourceField] : [],
      targetFields: targetField ? [targetField] : [],
    });

    this.adding.set(false);
  }

  cardinalitiesForType(
    type: string,
  ): [string, string] {
    switch (type) {
      case 'ONE_TO_ONE':
        return ['1', '1'];

      case 'ONE_TO_MANY':
        return ['1', 'N'];

      case 'MANY_TO_ONE':
        return ['N', '1'];

      case 'MANY_TO_MANY':
        return ['N', 'N'];

      default:
        return ['1', 'N'];
    }
  }

  fieldsForEntity(entityName: string): string[] {
    return (
      this.entities().find(item => item.name === entityName)?.fields
        .map(field => field.name) ?? []
    );
  }

  newSourceFields(): string[] {
    return this.fieldsForEntity(
      this.newDirection() === 'OUTGOING'
        ? this.entity().name
        : this.newEntity(),
    );
  }

  newTargetFields(): string[] {
    return this.fieldsForEntity(
      this.newDirection() === 'OUTGOING'
        ? this.newEntity()
        : this.entity().name,
    );
  }
}
