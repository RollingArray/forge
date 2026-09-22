import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

export type InspectorTab =
  | 'fields'
  | 'relationships'
  | 'constraints';

@Component({
  selector: 'app-entity-inspector-tabs',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-inspector-tabs.component.html',
  styleUrl: './entity-inspector-tabs.component.css',
})
export class EntityInspectorTabsComponent {
  readonly activeTab = input.required<InspectorTab>();
  readonly fieldCount = input(0);
  readonly relationshipCount = input(0);
  readonly constraintCount = input(0);

  readonly tabSelected = output<InspectorTab>();

  select(tab: InspectorTab): void {
    this.tabSelected.emit(tab);
  }
}
