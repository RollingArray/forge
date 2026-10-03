import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';

@Component({
  selector: 'app-workspace-scroll-area',
  standalone: true,
  templateUrl: './workspace-scroll-area.component.html',
  styleUrl: './workspace-scroll-area.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceScrollAreaComponent {}
