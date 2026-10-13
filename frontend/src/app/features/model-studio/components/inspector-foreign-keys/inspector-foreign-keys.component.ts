/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: inspector-foreign-keys.component.ts
 * Purpose: Presents foreign-key mappings for the selected entity.
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
import { ForgeForeignKey } from '../../../../core/interfaces/forge-foreign-key.interface';

@Component({
  selector: 'app-inspector-foreign-keys',
  standalone: true,
  imports: [EmptyInspectorStateComponent, InspectorShellComponent, InspectorRowComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './inspector-foreign-keys.component.html',
  styleUrl: './inspector-foreign-keys.component.css',
})
export class InspectorForeignKeysComponent {
  readonly foreignKeys = input<ForgeForeignKey[]>([]);
  readonly entityName = input.required<string>();
  readonly addForeignKey = output<string>();
  readonly editForeignKey = output<ForgeForeignKey>();
}
