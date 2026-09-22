import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { Activity } from '../../models/home.models';

import { QuickActionsComponent } from '../quick-actions/quick-actions.component';
import { RecentActivityComponent } from '../recent-activity/recent-activity.component';
import { HelpCardComponent } from '../help-card/help-card.component';

@Component({
  selector: 'app-home-right-rail',
  standalone: true,
  imports: [
    QuickActionsComponent,
    RecentActivityComponent,
    HelpCardComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './home-right-rail.component.html',
  styleUrl: './home-right-rail.component.css',
})
export class HomeRightRailComponent {
  readonly activities = input.required<Activity[]>();

  readonly quickActionSelected = output<string>();
  readonly viewAllActivity = output<void>();
  readonly documentationRequested = output<void>();
}
