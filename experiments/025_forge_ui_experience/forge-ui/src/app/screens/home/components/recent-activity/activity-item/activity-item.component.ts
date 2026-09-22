import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';

import { Activity } from '../../../models/home.models';

@Component({
  selector: 'app-activity-item',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './activity-item.component.html',
  styleUrl: './activity-item.component.css',
})
export class ActivityItemComponent {
  readonly activity = input.required<Activity>();
}
