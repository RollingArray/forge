import {
  ChangeDetectionStrategy,
  Component,
  output,
  signal,
} from '@angular/core';

@Component({
  selector: 'app-ask-forge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './ask-forge.component.html',
  styleUrl: './ask-forge.component.css',
})
export class AskForgeComponent {
  readonly closed = output<void>();
  readonly suggestionApproved = output<void>();

  readonly prompt = signal('');

  readonly isThinking = signal(false);
  readonly hasSuggestion = signal(false);

  submit(): void {
    const value = this.prompt().trim();

    if (!value || this.isThinking()) {
      return;
    }

    this.isThinking.set(true);
    this.hasSuggestion.set(false);

    window.setTimeout(() => {
      this.isThinking.set(false);
      this.hasSuggestion.set(true);
    }, 700);
  }

  updatePrompt(value: string): void {
    this.prompt.set(value);
  }

  approve(): void {
    this.suggestionApproved.emit();
    this.hasSuggestion.set(false);
    this.prompt.set('');
  }
}
