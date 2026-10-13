/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: inspector-relationships.component.ts
 * Purpose: Displays relationships involving the selected entity.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { EmptyInspectorStateComponent } from '../empty-inspector-state/empty-inspector-state.component';
import { InspectorShellComponent } from '../inspector-shell/inspector-shell.component';
import { InspectorRowComponent } from '../inspector-row/inspector-row.component';
import { ForgeSpecificationRelationship } from '../../../../core/interfaces/forge-specification-relationship.interface';

@Component({
  selector: 'app-inspector-relationships',
  standalone: true,
  imports: [EmptyInspectorStateComponent, InspectorShellComponent, InspectorRowComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './inspector-relationships.component.html',
  styleUrl: './inspector-relationships.component.css',
})
export class InspectorRelationshipsComponent {
  readonly relationships = input<ForgeSpecificationRelationship[]>([]);
  readonly otherSide = input.required<(relationship: ForgeSpecificationRelationship) => string>();
  readonly direction = input.required<(relationship: ForgeSpecificationRelationship) => string>();
  readonly addRelationship = output<void>();
  readonly editRelationship = output<ForgeSpecificationRelationship>();
  readonly deleteRelationship = output<ForgeSpecificationRelationship>();

  cardinality(type: string): string {
    const labels: Record<string, string> = {
      ONE_TO_ONE: '1..1',
      ONE_TO_MANY: '1..N',
      MANY_TO_ONE: 'N..1',
      MANY_TO_MANY: 'N..N',
    };
    return labels[type] ?? type;
  }

  cardinalityDescription(type: string): string {
    const labels: Record<string, string> = {
      ONE_TO_ONE: 'One to one',
      ONE_TO_MANY: 'One to many',
      MANY_TO_ONE: 'Many to one',
      MANY_TO_MANY: 'Many to many',
    };
    return labels[type] ?? 'Relationship';
  }

}
