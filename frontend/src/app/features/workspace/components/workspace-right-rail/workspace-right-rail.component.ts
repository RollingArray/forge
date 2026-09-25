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

import { QuickActionsComponent } from '../quick-actions/quick-actions.component';
import { RecentActivityComponent } from '../recent-activity/recent-activity.component';
import { HelpCardComponent } from '../help-card/help-card.component';

@Component({
  selector: 'app-workspace-right-rail',
  standalone: true,
  imports: [
    QuickActionsComponent,
    RecentActivityComponent,
    HelpCardComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workspace-right-rail.component.html',
  styleUrl: './workspace-right-rail.component.css',
})
export class WorkspaceRightRailComponent {
  readonly activities = input.required<Activity[]>();

  readonly quickActionSelected = output<string>();
  readonly viewAllActivity = output<void>();
  readonly documentationRequested = output<void>();
}
