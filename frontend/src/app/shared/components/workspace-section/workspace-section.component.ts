import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';

@Component({
  selector: 'app-workspace-section',
  standalone: true,
  templateUrl: './workspace-section.component.html',
  styleUrl: './workspace-section.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceSectionComponent {}
