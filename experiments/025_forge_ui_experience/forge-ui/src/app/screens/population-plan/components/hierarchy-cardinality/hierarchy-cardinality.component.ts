import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  effect,
  ElementRef,
  input,
  viewChild,
} from '@angular/core';

import { DecimalPipe } from '@angular/common';
import {
  Chart,
  registerables,
} from 'chart.js';

import {
  PopulationCardinalityItem,
  PopulationHierarchyNode,
} from '../../models/population-plan.models';

Chart.register(...registerables);

@Component({
  selector: 'app-hierarchy-cardinality',
  standalone: true,
  imports: [DecimalPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './hierarchy-cardinality.component.html',
  styleUrl: './hierarchy-cardinality.component.css',
})
export class HierarchyCardinalityComponent implements AfterViewInit {
  readonly nodes =
    input<readonly PopulationHierarchyNode[]>([]);

  readonly relationships =
    input<readonly PopulationCardinalityItem[]>([]);

  readonly hierarchyChart =
    viewChild<ElementRef<HTMLCanvasElement>>('hierarchyChart');

  readonly cardinalityChart =
    viewChild<ElementRef<HTMLCanvasElement>>('cardinalityChart');

  private hierarchyChartInstance: Chart | null = null;
  private cardinalityChartInstance: Chart | null = null;
  private viewReady = false;

  readonly maxLevel = () =>
    this.nodes().reduce(
      (max, node) =>
        Math.max(max, node.level),
      0,
    );

  readonly levelCount = () =>
    this.maxLevel() + 1;

  constructor() {
    effect(() => {
      this.nodes();
      this.relationships();

      if (this.viewReady) {
        this.renderCharts();
      }
    });
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.renderCharts();
  }

  private renderCharts(): void {
    this.renderHierarchyChart();
    this.renderCardinalityChart();
  }

  private renderHierarchyChart(): void {
    const canvas = this.hierarchyChart()?.nativeElement;

    if (!canvas) {
      return;
    }

    const levelTotals = new Map<number, number>();

    for (const node of this.nodes()) {
      levelTotals.set(
        node.level,
        (levelTotals.get(node.level) ?? 0) + node.resolved,
      );
    }

    const levels = Array.from(levelTotals.keys()).sort(
      (a, b) => a - b,
    );

    const labels = levels.map(
      (level) => `L${level}`,
    );

    const values = levels.map(
      (level) => levelTotals.get(level) ?? 0,
    );

    this.hierarchyChartInstance?.destroy();

    this.hierarchyChartInstance = new Chart(
      canvas,
      {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {
              label: 'Resolved population',
              data: values,
              borderWidth: 0,
              borderRadius: 4,
              barPercentage: 0.62,
              categoryPercentage: 0.72,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false,
            },
            tooltip: {
              callbacks: {
                label: (context) =>
                  ` ${Number(context.raw).toLocaleString()} records`,
              },
            },
          },
          scales: {
            x: {
              grid: {
                display: false,
              },
              border: {
                display: false,
              },
              ticks: {
                color: '#737a87',
                font: {
                  size: 10,
                },
              },
            },
            y: {
              beginAtZero: true,
              border: {
                display: false,
              },
              grid: {
                color: '#eef0f3',
              },
              ticks: {
                color: '#858c97',
                font: {
                  size: 9,
                },
                callback: (value) =>
                  Number(value).toLocaleString(),
              },
            },
          },
        },
      },
    );
  }

  private renderCardinalityChart(): void {
    const canvas = this.cardinalityChart()?.nativeElement;

    if (!canvas) {
      return;
    }

    const counts = new Map<string, number>();

    for (const relationship of this.relationships()) {
      const key =
        `${relationship.sourceCardinality}:${relationship.targetCardinality}`;

      counts.set(
        key,
        (counts.get(key) ?? 0) + 1,
      );
    }

    const labels = Array.from(counts.keys());
    const values = labels.map(
      (label) => counts.get(label) ?? 0,
    );

    this.cardinalityChartInstance?.destroy();

    this.cardinalityChartInstance = new Chart(
      canvas,
      {
        type: 'doughnut',
        data: {
          labels,
          datasets: [
            {
              data: values,
              borderWidth: 2,
              borderColor: '#ffffff',
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '68%',
          plugins: {
            legend: {
              position: 'right',
              labels: {
                color: '#596170',
                boxWidth: 10,
                boxHeight: 10,
                padding: 12,
                font: {
                  size: 10,
                },
              },
            },
            tooltip: {
              callbacks: {
                label: (context) =>
                  ` ${context.label}: ${context.raw} relationships`,
              },
            },
          },
        },
      },
    );
  }
}
