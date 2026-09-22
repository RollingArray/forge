import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';

@Component({
  selector: 'app-studio-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './studio-header.component.html',
  styleUrl: './studio-header.component.css',
})
export class StudioHeaderComponent {}
