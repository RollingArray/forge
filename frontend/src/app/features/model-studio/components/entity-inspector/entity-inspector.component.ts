import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import { InspectorNavigationComponent } from '../inspector-navigation/inspector-navigation.component';
import { InspectorHeaderComponent } from '../inspector-header/inspector-header.component';
import { InspectorFieldsComponent } from '../inspector-fields/inspector-fields.component';
import { InspectorRelationshipsComponent } from '../inspector-relationships/inspector-relationships.component';
import { InspectorKeysComponent } from '../inspector-keys/inspector-keys.component';
import { InspectorConstraintsComponent } from '../inspector-constraints/inspector-constraints.component';
import { InspectorForeignKeysComponent } from '../inspector-foreign-keys/inspector-foreign-keys.component';
import { ForgeConstraint } from '../../../../core/interfaces/forge-constraint.interface';
import { ForgeForeignKey } from '../../../../core/interfaces/forge-foreign-key.interface';
import { ForgeSpecificationEntity } from '../../../../core/interfaces/forge-specification-entity.interface';
import { ForgeSpecificationField } from '../../../../core/interfaces/forge-specification-field.interface';
import { ForgeSpecificationRelationship } from '../../../../core/interfaces/forge-specification-relationship.interface';
import { InspectorTab } from '../../../../core/types/inspector-tab.type';

@Component({
  selector: 'app-model-studio-entity-inspector',
  standalone: true,
  imports: [
    InspectorNavigationComponent,
    InspectorHeaderComponent,
    InspectorFieldsComponent,
    InspectorKeysComponent,
    InspectorRelationshipsComponent,
    InspectorForeignKeysComponent,
    InspectorConstraintsComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-inspector.component.html',
  styleUrl: './entity-inspector.component.css',
})
export class EntityInspectorComponent {
  readonly entity = input<ForgeSpecificationEntity | null>(null);

  readonly relationships = input<ForgeSpecificationRelationship[]>([]);

  readonly constraints = input<ForgeConstraint[]>([]);

  readonly foreignKeys = input<ForgeForeignKey[]>([]);

  readonly addField = output<void>();
  readonly addConstraint = output<void>();
  readonly editConstraint = output<ForgeConstraint>();
  readonly addRelationship = output<string>();
  readonly addForeignKey = output<string>();
  readonly editForeignKey = output<ForgeForeignKey>();
  readonly editRelationship = output<ForgeSpecificationRelationship>();
  readonly deleteRelationship = output<ForgeSpecificationRelationship>();
  readonly editField = output<ForgeSpecificationField>();
  readonly editIdentity = output<void>();
  readonly closed = output<void>();

  constraintsForEntity(): ForgeConstraint[] {
    const entityName = this.entity()?.name;
    if (!entityName) return [];

    return this.constraints().filter((constraint) => constraint.entity === entityName);
  }

  foreignKeysForEntity(): ForgeForeignKey[] {
    const entityName = this.entity()?.name;
    if (!entityName) return [];

    return this.foreignKeys().filter(
      (foreignKey) =>
        foreignKey.source.entity === entityName || foreignKey.target.entity === entityName,
    );
  }

  relationshipsForEntity(): ForgeSpecificationRelationship[] {
    const entityName = this.entity()?.name;
    if (!entityName) return [];

    return this.relationships().filter(
      (relationship) =>
        relationship.source.startsWith(`${entityName}.`) ||
        relationship.target.startsWith(`${entityName}.`),
    );
  }

  relationshipOtherSide(relationship: ForgeSpecificationRelationship): string {
    const entityName = this.entity()?.name;
    if (!entityName) return '';

    if (relationship.source.startsWith(`${entityName}.`)) {
      return relationship.target;
    }

    return relationship.source;
  }

  relationshipDirection(relationship: ForgeSpecificationRelationship): string {
    const entityName = this.entity()?.name;
    if (!entityName) return '';

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
    return this.entity()?.identity?.fields?.length ?? 0;
  }

  identityFields(): string[] {
    return this.entity()?.identity?.fields ?? [];
  }

  isIdentityField(fieldName: string): boolean {
    return this.identityFields().includes(fieldName);
  }
}
