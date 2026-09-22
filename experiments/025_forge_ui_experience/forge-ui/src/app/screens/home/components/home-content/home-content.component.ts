import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import {
  Metric,
  Session,
  Template,
} from '../../models/home.models';

import { MetricsComponent } from '../metrics/metrics.component';
import { RecentSessionsComponent } from '../recent-sessions/recent-sessions.component';
import { TemplatesComponent } from '../templates/templates.component';

@Component({
  selector: 'app-home-content',
  standalone: true,
  imports: [
    MetricsComponent,
    RecentSessionsComponent,
    TemplatesComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './home-content.component.html',
  styleUrl: './home-content.component.css',
})
export class HomeContentComponent {
  readonly metrics = input.required<Metric[]>();
  readonly sessions = input.required<Session[]>();
  readonly templates = input.required<Template[]>();

  readonly selectedSession = input<string>('');

  readonly newSession = output<void>();
  readonly sessionSelected = output<string>();
  readonly templateSelected = output<string>();
  readonly viewAllSessions = output<void>();
}
