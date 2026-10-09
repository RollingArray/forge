import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { StatusCardComponent } from '../../../../shared/components/status-card/status-card.component';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';
import { GenerationPipelineNode } from '../../../../shared/models/generation-pipeline.models';

@Component({
  selector: 'app-generation-pipeline',
  standalone: true,
  imports: [
    CommonModule,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    StatusCardComponent,
    WorkspaceScrollAreaComponent,
  ],
  templateUrl: './generation-pipeline.component.html',
  styleUrl: './generation-pipeline.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationPipelineComponent {
  readonly nodes = input<GenerationPipelineNode[]>([]);
  readonly loading = input(false);
  readonly ready = input(false);

  readonly completedCount = computed(
    () => this.nodes().filter((node) => node.status === 'COMPLETED').length,
  );

  readonly runningIndex = computed(() =>
    this.nodes().findIndex((node) => node.status === 'RUNNING'),
  );

  readonly totalGeneratedRows = computed(() =>
    this.nodes().reduce((total, node) => total + node.generatedRows, 0),
  );

  readonly totalTargetRows = computed(() =>
    this.nodes().reduce((total, node) => total + node.targetRows, 0),
  );

  readonly overallProgress = computed(() => {
    const target = this.totalTargetRows();

    return target > 0 ? this.totalGeneratedRows() / target : 0;
  });

  dependencyNode(dependencyName: string): GenerationPipelineNode | undefined {
    return this.nodes().find((node) => node.entityName === dependencyName);
  }

  dependencyStatusLabel(dependencyName: string): string {
    const dependency = this.dependencyNode(dependencyName);

    if (!dependency) {
      return 'Unknown';
    }

    switch (dependency.status) {
      case 'COMPLETED':
        return 'Generated';

      case 'RUNNING':
        return 'Generating';

      case 'QUEUED':
        return 'Queued';

      case 'FAILED':
        return 'Failed';

      case 'CANCELLED':
        return 'Cancelled';

      default:
        return 'Waiting';
    }
  }

  readonly executionSummary = computed(() => {
    const nodes = this.nodes();
    const runningIndex = this.runningIndex();

    if (runningIndex >= 0) {
      return `Executing entity ${runningIndex + 1} of ${nodes.length}`;
    }

    if (nodes.length > 0 && this.completedCount() === nodes.length) {
      return 'Generation complete';
    }

    return 'Generation ready';
  });

  readonly executionDetail = computed(() => {
    const nodes = this.nodes();

    return `${this.completedCount()} / ${nodes.length} completed`;
  });
}
