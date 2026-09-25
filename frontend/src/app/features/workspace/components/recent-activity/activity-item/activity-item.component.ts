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
}
