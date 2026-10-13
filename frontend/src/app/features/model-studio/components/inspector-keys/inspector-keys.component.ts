/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: inspector-keys.component.ts
 * Purpose: Presents entity identity fields and the identity editing action.
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

@Component({
  selector: 'app-inspector-keys',
  standalone: true,
  imports: [EmptyInspectorStateComponent, InspectorShellComponent, InspectorRowComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './inspector-keys.component.html',
  styleUrl: './inspector-keys.component.css',
})
export class InspectorKeysComponent {
  readonly identityFields = input<string[]>([]);
  readonly editIdentity = output<void>();
}
