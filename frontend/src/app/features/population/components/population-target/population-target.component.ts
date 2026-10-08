import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';

@Component({
  selector: 'app-population-target',
  standalone: true,
  imports: [
    WorkspaceHeaderComponent,
    WorkspaceSectionComponent,
  ],
  templateUrl: './population-target.component.html',
  styleUrl: './population-target.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PopulationTargetComponent {
  readonly targetRows = input<number | null>(null);
  readonly isDistributing = input(false);

  readonly targetChange = output<string>();
  readonly distribute = output<void>();

  onTargetChange(value: string): void {
    this.targetChange.emit(value);
  }

  onDistribute(): void {
    this.distribute.emit();
  }
}
