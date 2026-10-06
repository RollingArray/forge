import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { ChartOptions } from 'chart.js';

import { SpecificationValidationResult } from '../../../../core/interfaces/specification-validation.interface';
import { ChartComponent } from '../../../../shared/components/chart/chart.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';

@Component({
  selector: 'app-model-validation-entity-chart',
  standalone: true,
  imports: [
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    WorkspaceScrollAreaComponent,
    ChartComponent,
  ],
  templateUrl: './model-validation-entity-chart.component.html',
  styleUrl: './model-validation-entity-chart.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelValidationEntityChartComponent {
  readonly validation =
    input.required<SpecificationValidationResult>();

  readonly chartLabels = computed(() =>
    this.validation().entities.map((entity) => entity.name),
  );

  readonly chartHeight = computed(() => {
    const entityCount = this.validation().entities.length;
    return `${Math.max(400, entityCount * 24 + 80)}px`;
  });

  readonly chartDatasets = computed(() => [
    {
      label: 'Passed',
      data: this.validation().entities.map(
        (entity) =>
          Math.max(
            0,
            entity.checks - entity.errors - entity.warnings,
          ),
      ),
      backgroundColor: this.cssColor('--forge-success'),
      borderWidth: 0,
      borderRadius: 3,
      stack: 'validation',
    },
    {
      label: 'Warnings',
      data: this.validation().entities.map(
        (entity) => entity.warnings,
      ),
      backgroundColor: this.cssColor('--forge-warning'),
      borderWidth: 0,
      borderRadius: 3,
      stack: 'validation',
    },
    {
      label: 'Errors',
      data: this.validation().entities.map(
        (entity) => entity.errors,
      ),
      backgroundColor: this.cssColor('--forge-error'),
      borderWidth: 0,
      borderRadius: 3,
      stack: 'validation',
    },
  ]);

  readonly chartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: {
        position: 'top',
        align: 'start',
        labels: {
          boxWidth: 10,
          boxHeight: 10,
          usePointStyle: true,
          pointStyle: 'rectRounded',
          padding: 14,
          font: {
            size: 10,
          },
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      x: {
        stacked: true,
        beginAtZero: true,
        ticks: {
          precision: 0,
          font: {
            size: 9,
          },
        },
        title: {
          display: true,
          text: 'Checks',
          font: {
            size: 10,
          },
        },
        grid: {
          color: this.cssColor('--forge-border-subtle'),
        },
      },
      y: {
        stacked: true,
        ticks: {
          autoSkip: false,
          font: {
            size: 9,
          },
        },
        grid: {
          display: false,
        },
      },
    },
  };

  private cssColor(variable: string): string {
    return getComputedStyle(
      document.documentElement,
    )
      .getPropertyValue(variable)
      .trim();
  }
}
