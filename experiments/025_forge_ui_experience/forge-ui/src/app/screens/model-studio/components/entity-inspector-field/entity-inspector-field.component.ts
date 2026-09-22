import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { ModelField } from '../../models/model-studio.models';

@Component({
  selector: 'app-entity-inspector-field',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-inspector-field.component.html',
  styleUrl: './entity-inspector-field.component.css',
})
export class EntityInspectorFieldComponent {
  readonly field = input.required<ModelField>();
}
