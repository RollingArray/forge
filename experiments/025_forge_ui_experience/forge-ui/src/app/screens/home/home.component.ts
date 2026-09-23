import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';

import {
  Activity,
  Metric,
  QuickAction,
  Session,
  Template,
} from './models/home.models';

import {
  HOME_ACTIVITIES,
  HOME_METRICS,
  HOME_QUICK_ACTIONS,
  HOME_SESSIONS,
  HOME_TEMPLATES,
} from './data/home.mock';

import { SidebarComponent } from './components/sidebar/sidebar.component';
import { TopbarComponent } from './components/topbar/topbar.component';
import { WelcomeHeaderComponent } from './components/welcome-header/welcome-header.component';
import { HomeContentComponent } from './components/home-content/home-content.component';
import { HomeRightRailComponent } from './components/home-right-rail/home-right-rail.component';

import { ForgeNavigationService } from '../../core/navigation/forge-navigation.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    SidebarComponent,
    TopbarComponent,
    WelcomeHeaderComponent,
    HomeContentComponent,
    HomeRightRailComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent {
  private readonly navigation = inject(ForgeNavigationService);

  readonly metrics: Metric[] = HOME_METRICS;
  readonly sessions: Session[] = HOME_SESSIONS;
  readonly templates: Template[] = HOME_TEMPLATES;
  readonly activities: Activity[] = HOME_ACTIVITIES;
  readonly quickActions: QuickAction[] = HOME_QUICK_ACTIONS;

  readonly selectedSession = signal('');

  handleAction(action: string): void {
    console.info('[FORGE Home] action:', action);
  }

  handleNewSession(): void {
    this.navigation.navigateToStep('model');
  }

  handleSessionSelected(sessionName: string): void {
    this.selectedSession.set(sessionName);
    console.info('[FORGE Home] session selected:', sessionName);
  }

  handleTemplateSelected(templateName: string): void {
    console.info('[FORGE Home] template selected:', templateName);
  }

  handleQuickAction(action: string): void {
    this.handleAction(action);
  }

  handleViewAllSessions(): void {
    this.handleAction('view-all-sessions');
  }

  handleViewAllActivity(): void {
    this.handleAction('view-all-activity');
  }

  handleDocumentation(): void {
    this.handleAction('documentation');
  }

  handleTopbarAction(action: string): void {
    this.handleAction(action);
  }

  handleSidebarAction(action: string): void {
    this.handleAction(action);
  }
}
