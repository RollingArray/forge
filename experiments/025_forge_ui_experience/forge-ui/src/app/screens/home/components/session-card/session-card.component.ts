import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { Session } from '../../models/home.models';

@Component({
  selector: 'app-session-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './session-card.component.html',
  styleUrl: './session-card.component.css',
})
export class SessionCardComponent {
  readonly session = input.required<Session>();
  readonly selected = input(false);

  readonly selectedChange = output<string>();

  select(): void {
    this.selectedChange.emit(this.session().name);
  }
}
