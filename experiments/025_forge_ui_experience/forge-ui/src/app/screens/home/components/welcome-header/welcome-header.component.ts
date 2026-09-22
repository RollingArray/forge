import {
  ChangeDetectionStrategy,
  Component,
  output,
} from '@angular/core';

@Component({
  selector: 'app-home-welcome-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './welcome-header.component.html',
  styleUrl: './welcome-header.component.css',
})
export class WelcomeHeaderComponent {
  readonly newSession = output<void>();

  createSession(): void {
    this.newSession.emit();
  }
}
