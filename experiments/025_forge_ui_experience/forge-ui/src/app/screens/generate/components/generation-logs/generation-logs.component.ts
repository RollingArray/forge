import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';

@Component({
  selector: 'app-generation-logs',
  standalone: true,
  templateUrl: './generation-logs.component.html',
  styleUrl: './generation-logs.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenerationLogsComponent {}
