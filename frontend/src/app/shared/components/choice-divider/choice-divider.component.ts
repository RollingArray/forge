import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';

@Component({
  selector: 'app-choice-divider',
  standalone: true,
  templateUrl: './choice-divider.component.html',
  styleUrl: './choice-divider.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChoiceDividerComponent {}
