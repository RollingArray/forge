import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
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
  readonly closed = output<void>();
}
