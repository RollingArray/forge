import type { InspectorTab } from '../../../../core/types/inspector-tab.type';
import type { InspectorTabItem } from '../../../../core/interfaces/inspector-tab-item.interface';

import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-inspector-navigation',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './inspector-navigation.component.html',
  styleUrl: './inspector-navigation.component.css',
})
export class InspectorNavigationComponent {
  readonly activeTab = input.required<InspectorTab>();
  readonly fieldCount = input(0);
  readonly identityFieldCount = input(0);
  readonly relationshipCount = input(0);
  readonly foreignKeyCount = input(0);

  readonly tabSelected = output<InspectorTab>();

  readonly tabs = computed<InspectorTabItem[]>(() => [
    {
      id: 'FIELDS',
      label: 'Fields',
      shortLabel: 'Fields',
      icon: 'view_column',
      count: this.fieldCount(),
    },
    {
      id: 'KEYS',
      label: 'Keys',
      shortLabel: 'Keys',
      icon: 'key',
      count: this.identityFieldCount(),
    },
    {
      id: 'FOREIGN_KEYS',
      label: 'Foreign Keys',
      shortLabel: 'Foreign Keys',
      icon: 'link',
      count: this.foreignKeyCount(),
    },
    {
      id: 'RELATIONSHIPS',
      label: 'Relationships',
      shortLabel: 'Relations',
      icon: 'account_tree',
      count: this.relationshipCount(),
    },
    {
      id: 'CONSTRAINTS',
      label: 'Constraints',
      shortLabel: 'Constraints',
      icon: 'rule',
      count: 0,
    },
  ]);
}
