import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { Session } from '../../models/home.models';
import { SessionCardComponent } from '../session-card/session-card.component';

@Component({
  selector: 'app-home-recent-sessions',
  standalone: true,
  imports: [SessionCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './recent-sessions.component.html',
  styleUrl: './recent-sessions.component.css',
})
export class RecentSessionsComponent {
  readonly sessions = input.required<Session[]>();
  readonly selectedSession = input<string>('');

  readonly sessionSelected = output<string>();
  readonly newSession = output<void>();
  readonly viewAll = output<void>();

  selectSession(name: string): void {
    this.sessionSelected.emit(name);
  }

  createSession(): void {
    this.newSession.emit();
  }

  showAll(): void {
    this.viewAll.emit();
  }
}
