import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AIService } from '../../../core/services/ai.service';
import {
  AISemanticPreview,
  AISemanticPreviewStatus,
} from '../../../core/interfaces/ai-semantic-preview.interface';
import { FieldParameterHeaderComponent } from '../field-parameter-header/field-parameter-header.component';

@Component({
  selector: 'app-semantic-generator',
  standalone: true,
  imports: [
    FormsModule,
    FieldParameterHeaderComponent,
  ],
  templateUrl: './semantic-generator.component.html',
  styleUrl: './semantic-generator.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SemanticGeneratorComponent {
  private readonly aiService = inject(AIService);

  readonly description = input<string>('');
  readonly showValidation = input(false);

  readonly descriptionChange = output<string>();
  readonly previewReady = output<AISemanticPreview>();
  readonly previewCleared = output<void>();

  readonly descriptionValue = signal('');
  readonly preview = signal<AISemanticPreview | null>(null);
  readonly isGenerating = signal(false);
  readonly hasAttemptedPreview = signal(false);

  constructor() {
    effect(() => {
      this.descriptionValue.set(this.description());
    });
  }

  updateDescription(value: string): void {
    this.descriptionValue.set(value);
    this.descriptionChange.emit(value);

    if (this.preview()) {
      this.clearPreview();
    }
  }

  interpretAndPreview(): void {
    const description = this.descriptionValue().trim();

    this.hasAttemptedPreview.set(true);

    if (!description || this.isGenerating()) {
      return;
    }

    this.isGenerating.set(true);
    this.preview.set(null);

    this.aiService.previewSemanticValues(description).subscribe({
      next: (result) => {
        this.preview.set(result);
        this.isGenerating.set(false);
        this.previewReady.emit(result);
      },
      error: () => {
        this.preview.set({
          status: 'UNSUPPORTED',
          message: 'FORGE AI could not generate a semantic preview right now.',
          previewValues: [],
        });
        this.isGenerating.set(false);
      },
    });
  }

  clearPreview(): void {
    this.preview.set(null);
    this.hasAttemptedPreview.set(false);
    this.previewCleared.emit();
  }

  get previewStatus(): AISemanticPreviewStatus | null {
    return this.preview()?.status ?? null;
  }

  get canPreview(): boolean {
    return this.descriptionValue().trim().length > 0
      && !this.isGenerating();
  }
}
