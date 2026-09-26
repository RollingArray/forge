import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  signal,
} from '@angular/core';

import {
  ForgeSpecificationEntity,
  ForgeSpecificationField,
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

  readonly addField = output<void>();
  readonly editField = output<ForgeSpecificationField>();
  readonly editIdentity = output<void>();
  readonly closed = output<void>();

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
