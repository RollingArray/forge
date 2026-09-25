/**
 * File: tag-input.component.ts
 * Purpose: Reusable FORGE tag input/editor component.
 */

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  signal,
} from '@angular/core';

@Component({
  selector: 'app-tag-input',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './tag-input.component.html',
  styleUrl: './tag-input.component.css',
})
export class TagInputComponent {
  readonly tags = input<string[]>([]);
  readonly placeholder = input('Type a tag...');
  readonly maxTags = input(20);

  readonly tagsChange = output<string[]>();

  readonly inputValue = signal('');

  handleInput(value: string): void {
    this.inputValue.set(value);
  }

  handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      this.addTagsFromInput();
      return;
    }

    if (
      event.key === 'Backspace' &&
      !this.inputValue() &&
      this.tags().length
    ) {
      this.removeTag(this.tags().length - 1);
    }
  }

  handleBlur(): void {
    this.addTagsFromInput();
  }

  addTagsFromInput(): void {
    const value = this.inputValue().trim();

    if (!value) {
      return;
    }

    const incomingTags = value
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);

    const normalizedTags = this.normalizeTags([
      ...this.tags(),
      ...incomingTags,
    ]);

    this.tagsChange.emit(normalizedTags);
    this.inputValue.set('');
  }

  removeTag(index: number): void {
    this.tagsChange.emit(
      this.tags().filter((_, tagIndex) => tagIndex !== index),
    );
  }

  private normalizeTags(tags: string[]): string[] {
    const normalized: string[] = [];
    const maxTags = this.maxTags();

    for (const tag of tags) {
      const value = tag.trim();

      if (!value) {
        continue;
      }

      if (
        normalized.some(
          (existing) => existing.toLowerCase() === value.toLowerCase(),
        )
      ) {
        continue;
      }

      normalized.push(value);

      if (normalized.length >= maxTags) {
        break;
      }
    }

    return normalized;
  }
}
