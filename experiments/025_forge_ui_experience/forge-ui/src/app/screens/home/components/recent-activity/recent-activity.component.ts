import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { Activity } from '../../models/home.models';
import { ActivityItemComponent } from './activity-item/activity-item.component';

@Component({
  selector: 'app-recent-activity',
  standalone: true,
  imports: [ActivityItemComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './recent-activity.component.html',
  styleUrl: './recent-activity.component.css',
})
export class RecentActivityComponent {
  readonly activities = input.required<Activity[]>();
  readonly viewAll = output<void>();
}
