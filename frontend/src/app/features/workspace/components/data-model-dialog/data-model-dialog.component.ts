import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';

import { DataModel } from '../../../../core/interfaces/data-model.interface';
import { DataModelColor } from '../../../../core/enums/data-model-color.enum';
import { AIDataModelProposal } from '../../../../core/interfaces/ai-data-model-proposal.interface';
import { AIService } from '../../../../core/services/ai.service';
import { ColorPickerComponent } from '../../../../shared/components/color-picker/color-picker.component';
import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';
import { AiAssistPanelComponent } from '../../../../shared/components/ai-assist-panel/ai-assist-panel.component';
import { TagInputComponent } from '../../../../shared/components/tag-input/tag-input.component';

@Component({
  selector: 'app-data-model-dialog',
  standalone: true,
  imports: [
    FormsModule,
    ColorPickerComponent,
    FormDialogComponent,
    AiAssistPanelComponent,
    TagInputComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './data-model-dialog.component.html',
  styleUrl: './data-model-dialog.component.css',
})
export class DataModelDialogComponent {
  private readonly aiService = inject(AIService);
  private readonly destroyRef = inject(DestroyRef);

  readonly dataModel = input<DataModel | null>(null);

  readonly saved = output<{
    name: string;
    description: string;
    color: string;
    tags: string[];
  }>();

  readonly deleted = output<void>();
  readonly closed = output<void>();

  readonly name = signal('');
  readonly description = signal('');
  readonly tags = signal<string[]>([]);
  readonly selectedColor = signal<DataModelColor | null>(null);
  readonly deleteConfirming = signal(false);

  readonly aiCapabilityChecking = signal(true);
  readonly aiAvailable = signal(false);
  readonly aiModel = signal<string | null>(null);
  readonly aiMode = signal<string | null>(null);
  readonly aiCapabilityMessage = signal(
    'Checking whether FORGE AI assistance is available in this environment.',
  );

  readonly aiGenerating = signal(false);
  readonly aiProposal = signal<AIDataModelProposal | null>(null);
  readonly aiGenerationError = signal<string | null>(null);

  constructor() {
    effect(() => {
      const dataModel = this.dataModel();

      this.name.set(dataModel?.name ?? '');
      this.description.set(dataModel?.description ?? '');
      this.tags.set(dataModel?.tags ?? []);
      this.selectedColor.set(
        (dataModel?.color as DataModelColor | undefined) ?? null,
      );

      this.aiProposal.set(null);
      this.aiGenerationError.set(null);
    });

    this.loadAiCapabilities();
  }

  get isEditMode(): boolean {
    return this.dataModel() !== null;
  }

  get title(): string {
    return this.isEditMode ? 'Edit Data Model' : 'New Data Model';
  }

  get submitLabel(): string {
    return this.isEditMode ? 'Save Changes' : 'Create Data Model';
  }

  submit(): void {
    const name = this.name().trim();

    if (!name) {
      return;
    }

    this.saved.emit({
      name,
      description: this.description().trim(),
      color: this.selectedColor() ?? DataModelColor.Purple,
      tags: this.tags(),
    });
  }

  handleColorSelected(color: DataModelColor): void {
    this.selectedColor.set(color);
  }

  handleTagsChanged(value: string): void {
    this.tags.set(this.normalizeTags(value.split(',')));
  }

  delete(): void {
    if (this.isEditMode) {
      this.deleteConfirming.set(true);
    }
  }

  confirmDelete(): void {
    this.deleted.emit();
  }

  cancelDelete(): void {
    this.deleteConfirming.set(false);
  }

  close(): void {
    this.closed.emit();
  }

  handleAiGenerate(prompt: string): void {
    if (this.aiGenerating()) {
      return;
    }

    this.aiGenerating.set(true);
    this.aiGenerationError.set(null);
    this.aiProposal.set(null);

    this.aiService
      .suggestDataModel(prompt)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (proposal) => {
          this.aiProposal.set(proposal);
          this.aiGenerating.set(false);
        },
        error: (error) => {
          console.error(
            '[FORGE Workspace] AI Data Model proposal failed:',
            error,
          );

          this.aiGenerating.set(false);
          this.aiGenerationError.set(
            'FORGE AI could not generate a proposal. Please try again or continue manually.',
          );
        },
      });
  }

  useAiProposal(proposal: AIDataModelProposal): void {
    this.name.set(proposal.name);
    this.description.set(proposal.description);
    this.tags.set([...proposal.suggestedTags]);
  }

  regenerateAiProposal(): void {
    this.aiProposal.set(null);
    this.aiGenerationError.set(null);
  }

  private loadAiCapabilities(): void {
    this.aiCapabilityChecking.set(true);

    this.aiService
      .getCapabilities()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (capability) => {
          this.aiAvailable.set(capability.available);
          this.aiModel.set(capability.model);
          this.aiMode.set(capability.mode);
          this.aiCapabilityMessage.set(capability.message);
          this.aiCapabilityChecking.set(false);
        },
        error: () => {
          this.aiAvailable.set(false);
          this.aiCapabilityMessage.set(
            'FORGE AI is currently unavailable.',
          );
          this.aiCapabilityChecking.set(false);
        },
      });
  }

  private normalizeTags(values: string[]): string[] {
    const normalized: string[] = [];

    for (const value of values) {
      const tag = value.trim();

      if (!tag) {
        continue;
      }

      if (
        normalized.some(
          (existing) => existing.toLowerCase() === tag.toLowerCase(),
        )
      ) {
        continue;
      }

      normalized.push(tag);
    }

    return normalized.slice(0, 20);
  }
}
