import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { ContentGridComponent } from '../../../../shared/components/content-grid/content-grid.component';
import { ContentCardComponent } from '../../../../shared/components/content-card/content-card.component';
import { QualityEvidenceSection } from '../../../../core/interfaces/quality-evidence-section.interface';

@Component({
  selector: 'app-quality-evidence',
  standalone: true,
  imports: [
    WorkspaceHeaderComponent,
    WorkspaceScrollAreaComponent,
    WorkspaceSectionComponent,
    ContentGridComponent,
    ContentCardComponent,
  ],
  templateUrl: './quality-evidence.component.html',
  styleUrl: './quality-evidence.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QualityEvidenceComponent {
  readonly sections = input.required<readonly QualityEvidenceSection[]>();

  readonly sectionIcons: Record<string, string> = {
    'Population Fidelity': 'database',
    'Distribution Fidelity': 'chart_data',
    'Relationship Fidelity': 'account_tree',
    'Identity Space Utilization': 'fingerprint',
    'Statistical Fidelity': 'scatter_plot',
    Performance: 'speed',
    Validation: 'verified_user',
  };

  iconFor(title: string): string {
    return this.sectionIcons[title] ?? 'analytics';
  }
}
