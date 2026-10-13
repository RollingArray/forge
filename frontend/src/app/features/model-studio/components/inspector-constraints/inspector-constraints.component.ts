/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: inspector-constraints.component.ts
 * Purpose: Presents constraints for the selected entity.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { EmptyInspectorStateComponent } from '../empty-inspector-state/empty-inspector-state.component';
import { InspectorRowComponent } from '../inspector-row/inspector-row.component';
import { InspectorShellComponent } from '../inspector-shell/inspector-shell.component';
import { ForgeConstraint } from '../../../../core/interfaces/forge-constraint.interface';

@Component({
  selector: 'app-inspector-constraints',
  standalone: true,
  imports: [EmptyInspectorStateComponent, InspectorShellComponent, InspectorRowComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './inspector-constraints.component.html',
  styleUrl: './inspector-constraints.component.css',
})
export class InspectorConstraintsComponent {
  readonly constraints = input<ForgeConstraint[]>([]);
  readonly addConstraint = output<void>();
  readonly editConstraint = output<ForgeConstraint>();
}
