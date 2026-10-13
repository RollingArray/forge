import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { EmptyInspectorStateComponent } from '../empty-inspector-state/empty-inspector-state.component';
import { InspectorShellComponent } from '../inspector-shell/inspector-shell.component';
import { InspectorRowComponent } from '../inspector-row/inspector-row.component';
import { ForgeSpecificationEntity } from '../../../../core/interfaces/forge-specification-entity.interface';
import { ForgeSpecificationField } from '../../../../core/interfaces/forge-specification-field.interface';

@Component({
  selector: 'app-inspector-fields',
  standalone: true,
  imports: [EmptyInspectorStateComponent, InspectorShellComponent, InspectorRowComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './inspector-fields.component.html',
  styleUrl: './inspector-fields.component.css',
})
export class InspectorFieldsComponent {
  readonly entity = input.required<ForgeSpecificationEntity>();
  readonly identityFields = input<string[]>([]);

  readonly addField = output<void>();
  readonly editField = output<ForgeSpecificationField>();

  isIdentityField(fieldName: string): boolean {
    return this.identityFields().includes(fieldName);
  }
}
