import {
  ChangeDetectionStrategy,
  Component,
  effect,
  input,
  output,
  signal,
} from '@angular/core';

import {
  ForgeSpecificationEntity,
  ForgeSpecificationField,
} from '../../../../core/interfaces/forge-specification.interface';

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
  readonly identitySaved = output<string[]>();
  readonly closed = output<void>();

  readonly selectedIdentityFields = signal<string[]>([]);

  constructor() {
    effect(() => {
      this.selectedIdentityFields.set(
        [...(this.entity().identity?.fields ?? [])],
      );
    });
  }

  isIdentityField(fieldName: string): boolean {
    return this.selectedIdentityFields().includes(fieldName);
  }

  identityFieldCount(): number {
    return this.selectedIdentityFields().length;
  }

  toggleIdentityField(fieldName: string): void {
    const current = this.selectedIdentityFields();

    if (current.includes(fieldName)) {
      this.selectedIdentityFields.set(
        current.filter((field) => field !== fieldName),
      );
      return;
    }

    this.selectedIdentityFields.set([
      ...current,
      fieldName,
    ]);
  }

  saveIdentity(): void {
    const fields = this.selectedIdentityFields();

    if (fields.length === 0) {
      return;
    }

    this.identitySaved.emit([...fields]);
  }
}
