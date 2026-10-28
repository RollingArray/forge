import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { ChartOptions } from 'chart.js';

import { ChartComponent } from '../../../../shared/components/chart/chart.component';
import { ContentCardComponent } from '../../../../shared/components/content-card/content-card.component';
import { MetricGridComponent } from '../../../../shared/components/metric-grid/metric-grid.component';
import { MetricCardData } from '../../../../shared/components/metric-grid/metric-card-data';
import { WorkspaceSimpleTableComponent } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.component';
import { WorkspaceSimpleTableColumn } from '../../../../shared/components/workspace-simple-table/workspace-simple-table.models';

@Component({
  selector: 'app-population-fidelity-visualization',
  standalone: true,
  imports: [ContentCardComponent, ChartComponent, MetricGridComponent, WorkspaceSimpleTableComponent],
  templateUrl: './population-fidelity-visualization.component.html',
  styleUrl: './population-fidelity-visualization.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PopulationFidelityVisualizationComponent {
  readonly profile = input.required<Record<string, unknown>>();

  readonly metrics = computed<MetricCardData[]>(() => [
    {
      label: 'Total requested',
      value: this.formatNumber(this.requestedRows()),
      description: 'Rows planned for generation',
      icon: 'playlist_add_check',
    },
    {
      label: 'Total generated',
      value: this.formatNumber(this.generatedRows()),
      description: 'Rows actually generated',
      icon: 'database',
    },
    {
      label: 'Row-count difference',
      value: this.formatNumber(this.difference()),
      description: 'Generated minus requested',
      icon: 'difference',
    },
    {
      label: 'Population fidelity',
      value: this.fidelityRate(),
      description: 'Agreement with requested row counts',
      icon: 'verified',
    },
  ]);

  readonly tableColumns: readonly WorkspaceSimpleTableColumn<{
    name: string;
    requested: string;
    generated: string;
    difference: string;
    fidelity: string;
  }>[] = [
    { key: 'name', label: 'Entity', width: 'minmax(160px, 1fr)' },
    { key: 'requested', label: 'Requested', type: 'number', width: '115px', align: 'right' },
    { key: 'generated', label: 'Generated', type: 'number', width: '115px', align: 'right' },
    { key: 'difference', label: 'Difference', type: 'number', width: '115px', align: 'right' },
    { key: 'fidelity', label: 'Fidelity', width: '100px', align: 'right' },
  ];

  private readonly entities = computed(() => this.asRecord(this.profile()['entities']));

  readonly requestedRows = computed(() =>
    this.numberValue(this.profile()['total_requested_rows']),
  );

  readonly generatedRows = computed(() =>
    this.numberValue(this.profile()['total_generated_rows']),
  );

  readonly difference = computed(() =>
    this.numberValue(this.profile()['difference']),
  );

  readonly fidelityRate = computed(() => {
    const value = this.numberValue(this.profile()['fidelity_rate']);
    return value === null ? 'Not available' : `${(value * 100).toFixed(1)}%`;
  });

  readonly entityCount = computed(() => Object.keys(this.entities()).length);

  readonly chartLabels = computed(() => Object.keys(this.entities()));

  readonly entityRows = computed(() =>
    Object.entries(this.entities()).map(([name, raw]) => {
      const entity = this.asRecord(raw);
      const requested = this.numberValue(entity['requested_rows']);
      const generated = this.numberValue(entity['generated_rows']);
      const difference = requested === null || generated === null
        ? null
        : generated - requested;

      let fidelity: number | null = null;
      if (requested !== null && generated !== null) {
        fidelity = requested === 0
          ? (generated === 0 ? 1 : 0)
          : Math.max(0, 1 - Math.abs(generated - requested) / requested);
      }

      return {
        name,
        requested: this.formatNumber(requested),
        generated: this.formatNumber(generated),
        difference: this.formatNumber(difference),
        fidelity: fidelity === null ? 'Not available' : `${(fidelity * 100).toFixed(1)}%`,
      };
    }),
  );

  readonly chartDatasets = computed(() => [
    {
      label: 'Requested rows',
      data: Object.values(this.entities()).map((entity) =>
        this.numberValue(this.asRecord(entity)['requested_rows']) ?? 0,
      ),
      backgroundColor: this.cssColor('--forge-primary'),
      borderRadius: 4,
      borderSkipped: false,
      maxBarThickness: 18,
    },
    {
      label: 'Generated rows',
      data: Object.values(this.entities()).map((entity) =>
        this.numberValue(this.asRecord(entity)['generated_rows']) ?? 0,
      ),
      backgroundColor: this.cssColor('--forge-success'),
      borderRadius: 4,
      borderSkipped: false,
      maxBarThickness: 18,
    },
  ]);

  readonly chartHeight = computed(() =>
    `${Math.max(240, this.entityCount() * 48 + 76)}px`,
  );

  readonly chartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: {
        position: 'top',
        align: 'start',
        labels: {
          usePointStyle: true,
          pointStyle: 'rectRounded',
          boxWidth: 9,
          boxHeight: 9,
          padding: 16,
          font: { size: 11 },
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: {
          precision: 0,
          font: { size: 10 },
        },
        title: {
          display: true,
          text: 'Rows',
          font: { size: 11 },
        },
        grid: {
          color: this.cssColor('--forge-border-subtle'),
        },
      },
      y: {
        ticks: {
          autoSkip: false,
          font: { size: 10 },
        },
        grid: { display: false },
      },
    },
  };

  private formatNumber(value: number | null): string {
    return value === null ? 'Not available' : value.toLocaleString('en-US');
  }

  private numberValue(value: unknown): number | null {
    if (value === null || value === undefined || value === '') {
      return null;
    }

    const number = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(number) ? number : null;
  }

  private asRecord(value: unknown): Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {};
  }

  private cssColor(variable: string): string {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(variable)
      .trim();
  }
}
