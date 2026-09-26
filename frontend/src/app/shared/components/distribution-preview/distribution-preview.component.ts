import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
  input,
} from '@angular/core';
import {
  Chart,
  ChartConfiguration,
  registerables,
} from 'chart.js';

Chart.register(...registerables);

export type DistributionPreviewType =
  | 'uniform'
  | 'normal'
  | 'discrete-uniform';

@Component({
  selector: 'app-distribution-preview',
  standalone: true,
  templateUrl: './distribution-preview.component.html',
  styleUrl: './distribution-preview.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DistributionPreviewComponent
  implements AfterViewInit, OnChanges, OnDestroy
{
  readonly type = input.required<DistributionPreviewType>();

  @ViewChild('canvas', { static: true })
  private readonly canvas!: ElementRef<HTMLCanvasElement>;

  private chart?: Chart;

  ngAfterViewInit(): void {
    this.renderChart();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['type'] && this.canvas) {
      this.renderChart();
    }
  }

  ngOnDestroy(): void {
    this.chart?.destroy();
  }

  private renderChart(): void {
    this.chart?.destroy();

    const context = this.canvas.nativeElement.getContext('2d');

    if (!context) {
      return;
    }

    const isDiscrete = this.type() === 'discrete-uniform';
    const values = this.getValues();
    const labels = this.getLabels();

    const configuration: ChartConfiguration = {
      type: isDiscrete ? 'bar' : 'line',
      data: {
        labels,
        datasets: [
          {
            data: values,
            borderColor: '#7657d9',
            backgroundColor: 'transparent',
            borderWidth: 2,
            borderRadius: isDiscrete ? 2 : 0,
            barPercentage: 0.58,
            categoryPercentage: 0.72,
            pointRadius: 0,
            pointHoverRadius: 0,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            enabled: false,
          },
        },
        scales: {
          x: {
            display: true,
            grid: {
              display: false,
            },
            border: {
              display: false,
            },
            ticks: {
              color: '#756d82',
              font: {
                size: 9,
                weight: 600,
              },
              padding: 2,
            },
          },
          y: {
            display: false,
            min: 0,
            grid: {
              display: false,
            },
            border: {
              display: false,
            },
          },
        },
      },
    };

    this.chart = new Chart(context, configuration);
  }

  private getLabels(): string[] {
    switch (this.type()) {
      case 'normal':
        return ['20', '35', '45', '50', '55', '65', '80'];

      case 'discrete-uniform':
        return ['1', '2', '3', '4', '5', '6', '7', '8', '9'];

      case 'uniform':
      default:
        return ['10', '30', '40', '50', '60', '70', '90'];
    }
  }

  private getValues(): number[] {
    switch (this.type()) {
      case 'normal':
        return [1, 2, 4, 7, 10, 7, 4];

      case 'discrete-uniform':
        return [4, 4, 4, 4, 4, 4, 4, 4, 4];

      case 'uniform':
      default:
        return [4, 4, 4, 4, 4, 4, 4];
    }
  }
}
