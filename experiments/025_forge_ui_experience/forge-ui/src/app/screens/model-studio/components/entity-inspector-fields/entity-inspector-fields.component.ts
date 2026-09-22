import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import {
  ModelEntity,
  ModelField,
} from '../../models/model-studio.models';

import { EntityInspectorFieldComponent } from '../entity-inspector-field/entity-inspector-field.component';

@Component({
  selector: 'app-entity-inspector-fields',
  standalone: true,
  imports: [EntityInspectorFieldComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-inspector-fields.component.html',
  styleUrl: './entity-inspector-fields.component.css',
})
export class EntityInspectorFieldsComponent {
  readonly entity = input.required<ModelEntity>();

  readonly addField = output<void>();

  readonly isCompositeKey = () =>
    this.entity().primaryKey.composite;

  add(): void {
    this.addField.emit();
  }
}
