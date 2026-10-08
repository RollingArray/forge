import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { ChartOptions } from 'chart.js';

import { SpecificationValidationResult } from '../../../../core/interfaces/specification-validation.interface';
import { ChartComponent } from '../../../../shared/components/chart/chart.component';
import { WorkspaceHeaderComponent } from '../../../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceScrollAreaComponent } from '../../../../shared/components/workspace-scroll-area/workspace-scroll-area.component';

@Component({
  selector: 'app-model-validation-status-chart',
  standalone: true,
  imports: [
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    ChartComponent,
    WorkspaceScrollAreaComponent,
  ],
  templateUrl: './model-validation-status-chart.component.html',
  styleUrl: './model-validation-status-chart.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelValidationStatusChartComponent {
  readonly validation = input.required<SpecificationValidationResult>();

  readonly chartLabels = ['Passed', 'Warnings', 'Errors'];

  readonly chartDatasets = computed(() => [
    {
      data: [this.validation().passed, this.validation().warnings, this.validation().errors],
      backgroundColor: [
        this.cssColor('--forge-success'),
        this.cssColor('--forge-warning'),
        this.cssColor('--forge-error'),
      ],
      borderWidth: 0,
      hoverOffset: 4,
    },
  ]);

  readonly chartOptions: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '68%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          boxWidth: 10,
          boxHeight: 10,
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 14,
          font: {
            size: 10,
          },
          generateLabels: () => {
            const labels = ['Passed', 'Warnings', 'Errors'];
            const values = [
              this.validation().passed,
              this.validation().warnings,
              this.validation().errors,
            ];
            const colors = [
              this.cssColor('--forge-success'),
              this.cssColor('--forge-warning'),
              this.cssColor('--forge-error'),
            ];

            return labels.map((label, index) => ({
              text: `${label}    ${values[index]}`,
              fillStyle: colors[index],
              strokeStyle: 'transparent',
              lineWidth: 0,
              hidden: false,
              index,
            }));
          },
        },
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const value = context.parsed;
            return ` ${context.label}: ${value}`;
          },
        },
      },
    },
  };

  private cssColor(variable: string): string {
    return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  }
}
