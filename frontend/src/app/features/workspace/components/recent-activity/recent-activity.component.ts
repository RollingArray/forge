/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: recent-activity.component.ts
 * Purpose: Defines the recent activity Workspace component.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { Activity } from '../../../../core/interfaces/activity.interface';
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
