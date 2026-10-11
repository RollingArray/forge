/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: workspace-right-rail.component.ts
 * Purpose: Defines the workspace right rail Workspace component.
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

import { RecentActivityComponent } from '../recent-activity/recent-activity.component';

@Component({
  selector: 'app-workspace-right-rail',
  standalone: true,
  imports: [RecentActivityComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workspace-right-rail.component.html',
  styleUrl: './workspace-right-rail.component.css',
})
export class WorkspaceRightRailComponent {
  readonly activities = input.required<Activity[]>();

  readonly viewAllActivity = output<void>();
}
