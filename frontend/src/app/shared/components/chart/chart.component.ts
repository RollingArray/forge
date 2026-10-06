import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  effect,
  input,
  signal,
  viewChild,
} from '@angular/core';
import {
  Chart,
  ChartConfiguration,
  ChartOptions,
  ChartType,
  registerables,
} from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-chart',
  standalone: true,
  templateUrl: './chart.component.html',
  styleUrl: './chart.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChartComponent
  implements AfterViewInit, OnDestroy
{
  readonly type = input.required<ChartType>();
  readonly labels = input.required<readonly string[]>();
  readonly datasets =
    input.required<ChartConfiguration['data']['datasets']>();

  readonly options =
    input<ChartOptions<any>>();

  private readonly canvas =
    viewChild<ElementRef<HTMLCanvasElement>>('chart');

  private readonly viewReady = signal(false);

  private chart?: Chart;

  constructor() {
    effect(() => {
      const type = this.type();
      const labels = this.labels();
      const datasets = this.datasets();
      const options = this.options();

      if (!this.viewReady() || !this.canvas()) {
        return;
      }

      this.renderChart(
        type,
        labels,
        datasets,
        options,
      );
    });
  }

  ngAfterViewInit(): void {
    this.viewReady.set(true);
  }

  ngOnDestroy(): void {
    this.chart?.destroy();
  }

  private renderChart(
    type: ChartType,
    labels: readonly string[],
    datasets: ChartConfiguration['data']['datasets'],
    options?: ChartOptions<any>,
  ): void {
    const canvas = this.canvas()?.nativeElement;

    if (!canvas) {
      return;
    }

    this.chart?.destroy();

    this.chart = new Chart(canvas, {
      type,
      data: {
        labels: [...labels],
        datasets: [...datasets],
      },
      options,
    });
  }
}
