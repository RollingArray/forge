import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  signal,
} from '@angular/core';

import {
  ForgeConstraint,
  ForgeSpecificationEntity,
  ForgeSpecificationField,
  ForgeSpecificationRelationship,
} from '../../../../core/interfaces/forge-specification.interface';

type InspectorTab =
  | 'FIELDS'
  | 'KEYS'
  | 'RELATIONSHIPS'
  | 'CONSTRAINTS';

@Component({
  selector: 'app-model-studio-entity-inspector',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-inspector.component.html',
  styleUrl: './entity-inspector.component.css',
})
export class EntityInspectorComponent {
  readonly entity = input.required<ForgeSpecificationEntity>();

  readonly relationships =
    input<ForgeSpecificationRelationship[]>([]);

  readonly constraints = input<ForgeConstraint[]>([]);

  readonly addField = output<void>();
  readonly addConstraint = output<void>();
  readonly editConstraint = output<ForgeConstraint>();
  readonly addRelationship = output<string>();
  readonly editRelationship =
    output<ForgeSpecificationRelationship>();
  readonly editField = output<ForgeSpecificationField>();
  readonly editIdentity = output<void>();
  readonly closed = output<void>();

  constraintsForEntity(): ForgeConstraint[] {
    const entityName = this.entity().name;

    return this.constraints().filter(
      (constraint) => constraint.entity === entityName,
    );
  }

  relationshipsForEntity(): ForgeSpecificationRelationship[] {
    const entityName = this.entity().name;

    return this.relationships().filter(
      (relationship) =>
        relationship.source.startsWith(`${entityName}.`) ||
        relationship.target.startsWith(`${entityName}.`),
    );
  }

  relationshipOtherSide(
    relationship: ForgeSpecificationRelationship,
  ): string {
    const entityName = this.entity().name;

    if (relationship.source.startsWith(`${entityName}.`)) {
      return relationship.target;
    }

    return relationship.source;
  }

  relationshipDirection(
    relationship: ForgeSpecificationRelationship,
  ): string {
    const entityName = this.entity().name;

    if (relationship.source.startsWith(`${entityName}.`)) {
      return 'Connects to';
    }

    return 'Connected from';
  }

  readonly activeTab = signal<InspectorTab>('FIELDS');

  selectTab(tab: InspectorTab): void {
    this.activeTab.set(tab);
  }

  identityFieldCount(): number {
    return this.entity().identity?.fields?.length ?? 0;
  }

  identityFields(): string[] {
    return this.entity().identity?.fields ?? [];
  }

  isIdentityField(fieldName: string): boolean {
    return this.identityFields().includes(fieldName);
  }
}
