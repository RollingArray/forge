import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ForgeSpecificationEntity } from '../../../../core/interfaces/forge-specification-entity.interface';

@Component({
  selector: 'app-inspector-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './inspector-header.component.html',
  styleUrl: './inspector-header.component.css',
})
export class InspectorHeaderComponent {
  readonly entity = input.required<ForgeSpecificationEntity>();
  readonly closed = output<void>();
  readonly edit = output<void>();
}
