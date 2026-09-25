/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: activity-item.component.ts
 * Purpose: Defines the activity item Workspace component.
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
} from '@angular/core';

import { Activity } from '../../../../../core/interfaces/activity.interface';

@Component({
  selector: 'app-activity-item',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './activity-item.component.html',
  styleUrl: './activity-item.component.css',
})
export class ActivityItemComponent {
  readonly activity = input.required<Activity>();

  formatTime(value: string): string {
    const timestamp = new Date(value);

    if (Number.isNaN(timestamp.getTime())) {
      return value;
    }

    const elapsedMilliseconds = Date.now() - timestamp.getTime();
    const elapsedMinutes = Math.floor(
      elapsedMilliseconds / (1000 * 60),
    );

    if (elapsedMinutes < 1) {
      return 'Just now';
    }

    if (elapsedMinutes < 60) {
      return `${elapsedMinutes} min ago`;
    }

    const elapsedHours = Math.floor(elapsedMinutes / 60);

    if (elapsedHours < 24) {
      return `${elapsedHours} hr ago`;
    }

    const elapsedDays = Math.floor(elapsedHours / 24);

    if (elapsedDays === 1) {
      return 'Yesterday';
    }

    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(timestamp);
  }
}
