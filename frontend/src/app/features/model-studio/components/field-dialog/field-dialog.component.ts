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

import { ForgeSpecificationField } from '../../../../core/interfaces/forge-specification.interface';
import { AIService } from '../../../../core/services/ai.service';
import { AiAssistPanelComponent } from '../../../../shared/components/ai-assist-panel/ai-assist-panel.component';
import { ChoiceCardComponent } from '../../../../shared/components/choice-card/choice-card.component';
import { DistributionPreviewComponent } from '../../../../shared/components/distribution-preview/distribution-preview.component';
import { FormDialogComponent } from '../../../../shared/components/form-dialog/form-dialog.component';
import { FieldParameterHeaderComponent } from '../../../../shared/components/field-parameter-header/field-parameter-header.component';
import { PatternGeneratorComponent } from '../../../../shared/components/pattern-generator/pattern-generator.component';

export type FieldType =
  | 'IDENTIFIER'
  | 'STRING'
  | 'INTEGER'
  | 'DECIMAL'
  | 'BOOLEAN'
  | 'CATEGORICAL';

export type FieldDraft = {
  name: string;
  type: FieldType;
  identity?: {
    strategy: 'SEQUENTIAL_ID';
  };
  generation?: {
    strategy: 'RANDOM';
    distribution?: string;
    generator?: string;
    parameters?: Record<string, unknown>;
  };
};

@Component({
  selector: 'app-model-studio-field-dialog',
  standalone: true,
  imports: [
    FormsModule,
    FormDialogComponent,
    AiAssistPanelComponent,
    PatternGeneratorComponent,
    FieldParameterHeaderComponent,
    ChoiceCardComponent,
    DistributionPreviewComponent,
],
  templateUrl: './field-dialog.component.html',
  styleUrl: './field-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FieldDialogComponent {
  private readonly aiService = inject(AIService);
  private readonly destroyRef = inject(DestroyRef);

  readonly field = input<ForgeSpecificationField | null>(null);

  readonly saved = output<FieldDraft>();
  readonly closed = output<void>();

  readonly name = signal('');
  readonly type = signal<FieldType>('STRING');

  readonly distribution = signal('');
  readonly generator = signal('');

  readonly minimum = signal('');
  readonly maximum = signal('');
  readonly pattern = signal('');
  readonly semanticDescription = signal('');
  readonly characterSet = signal<'ALPHA' | 'DIGITS' | 'ALPHANUMERIC'>(
    'ALPHANUMERIC',
  );
  readonly minimumLength = signal('');
  readonly maximumLength = signal('');

  readonly categoricalValues = signal('');

  readonly showValidation = signal(false);

  readonly aiCapabilityChecking = signal(true);
  readonly aiAvailable = signal(false);
  readonly aiModel = signal<string | null>(null);
  readonly aiMode = signal<string | null>(null);
  readonly aiCapabilityMessage = signal(
    'Field-specific FORGE AI assistance is not available yet.',
  );

  constructor() {
    effect(() => {
      const field = this.field();

      this.reset();

      if (!field) {
        return;
      }

      this.name.set(field.name);
      this.type.set(field.type as FieldType);

      const generation = field.generation;
      if (!generation) {
        return;
      }

      this.distribution.set(generation.distribution ?? '');
      this.generator.set(
        typeof generation.generator === 'string'
          ? generation.generator
          : '',
      );

      const parameters = generation.parameters ?? {};

      this.minimum.set(
        parameters['minimum'] !== undefined
          ? String(parameters['minimum'])
          : '',
      );

      this.maximum.set(
        parameters['maximum'] !== undefined
          ? String(parameters['maximum'])
          : '',
      );

      this.pattern.set(
        typeof parameters['pattern'] === 'string'
          ? parameters['pattern']
          : '',
      );

      this.semanticDescription.set(
        typeof parameters['description'] === 'string'
          ? parameters['description']
          : '',
      );

      this.characterSet.set(
        (parameters['character_set'] as
          | 'ALPHA'
          | 'DIGITS'
          | 'ALPHANUMERIC'
          | undefined) ?? 'ALPHANUMERIC',
      );

      this.minimumLength.set(
        parameters['minimum_length'] !== undefined
          ? String(parameters['minimum_length'])
          : '',
      );

      this.maximumLength.set(
        parameters['maximum_length'] !== undefined
          ? String(parameters['maximum_length'])
          : '',
      );

      const values = parameters['values'];

      this.categoricalValues.set(
        Array.isArray(values)
          ? values.map((value) => String(value)).join(', ')
          : '',
      );
    });

    this.loadAiCapabilities();
  }

  get isEditMode(): boolean {
    return this.field() !== null;
  }

  get title(): string {
    return this.isEditMode ? 'Edit Field' : 'Add Field';
  }

  get submitLabel(): string {
    return this.isEditMode ? 'Save Changes' : 'Add Field';
  }

  get showDistribution(): boolean {
    return (
      this.type() === 'INTEGER' ||
      this.type() === 'DECIMAL'
    );
  }

  get showStringGenerator(): boolean {
    return this.type() === 'STRING';
  }

  get showParameters(): boolean {
    if (this.type() === 'INTEGER') {
      return (
        this.distribution() === 'UNIFORM' ||
        this.distribution() === 'DISCRETE_UNIFORM'
      );
    }

    if (this.type() === 'DECIMAL') {
      return (
        this.distribution() === 'UNIFORM' ||
        this.distribution() === 'NORMAL'
      );
    }

    if (this.type() === 'CATEGORICAL') {
      return this.distribution() === 'CATEGORICAL';
    }

    return false;
  }

  get showRandomStringParameters(): boolean {
    return (
      this.type() === 'STRING' &&
      this.generator() === 'RANDOM_STRING'
    );
  }

  get showPatternParameters(): boolean {
    return (
      this.type() === 'STRING' &&
      this.generator() === 'PATTERN'
    );
  }

  get showSemanticParameters(): boolean {
    return (
      this.type() === 'STRING' &&
      this.generator() === 'SEMANTIC'
    );
  }

  canSave(): boolean {
    if (!this.name().trim()) {
      return false;
    }

    if (this.type() === 'IDENTIFIER' || this.type() === 'BOOLEAN') {
      return true;
    }

    if (this.type() === 'CATEGORICAL') {
      return this.isCategoricalConfigurationValid();
    }

    if (this.type() === 'STRING') {
      return this.isStringConfigurationValid();
    }

    if (this.type() === 'INTEGER' || this.type() === 'DECIMAL') {
      return this.isNumericConfigurationValid();
    }

    return false;
  }

  private isStringConfigurationValid(): boolean {
    if (!this.generator()) {
      return false;
    }

    if (this.generator() === 'PATTERN') {
      return this.pattern().trim().length > 0;
    }

    if (this.generator() === 'SEMANTIC') {
      return this.semanticDescription().trim().length > 0;
    }

    if (this.generator() === 'RANDOM_STRING') {
      const minimum = this.toInteger(this.minimumLength());
      const maximum = this.toInteger(this.maximumLength());

      if (minimum === undefined || maximum === undefined) {
        return false;
      }

      return (
        minimum >= 1 &&
        maximum >= minimum &&
        !!this.characterSet()
      );
    }

    return false;
  }

  private isNumericConfigurationValid(): boolean {
    if (!this.distribution()) {
      return false;
    }

    if (
      this.distribution() === 'UNIFORM' ||
      this.distribution() === 'DISCRETE_UNIFORM'
    ) {
      const minimum = this.toNumber(this.minimum());
      const maximum = this.toNumber(this.maximum());

      if (minimum === undefined || maximum === undefined) {
        return false;
      }

      return minimum <= maximum;
    }

    if (this.distribution() === 'NORMAL') {
      return true;
    }

    return false;
  }

  private isCategoricalConfigurationValid(): boolean {
    const values = this.categoricalValues()
      .split(',')
      .map((value) => value.trim())
      .filter((value) => value.length > 0);

    if (values.length === 0) {
      return false;
    }

    return new Set(values).size === values.length;
  }

  get nameValidationMessage(): string {
    if (!this.showValidation() || this.name().trim()) {
      return '';
    }

    return 'Field name is required.';
  }

  get configurationValidationMessage(): string {
    if (!this.showValidation()) {
      return '';
    }

    if (this.type() === 'STRING') {
      if (!this.generator()) {
        return 'Choose how FORGE should generate this text.';
      }

      if (this.generator() === 'PATTERN' && !this.pattern().trim()) {
        return 'Enter a pattern for the generated values.';
      }

      if (
        this.generator() === 'SEMANTIC' &&
        !this.semanticDescription().trim()
      ) {
        return 'Describe what this field represents.';
      }

      if (this.generator() === 'RANDOM_STRING') {
        const minimum = this.toInteger(this.minimumLength());
        const maximum = this.toInteger(this.maximumLength());

        if (minimum === undefined || maximum === undefined) {
          return 'Enter both minimum and maximum lengths.';
        }

        if (minimum < 1) {
          return 'Minimum length must be at least 1.';
        }

        if (maximum < minimum) {
          return 'Maximum length must be greater than or equal to minimum length.';
        }

        if (!this.characterSet()) {
          return 'Choose a character set.';
        }
      }
    }

    if (this.type() === 'INTEGER' || this.type() === 'DECIMAL') {
      if (!this.distribution()) {
        return 'Choose how values should be distributed.';
      }

      if (
        this.distribution() === 'UNIFORM' ||
        this.distribution() === 'DISCRETE_UNIFORM'
      ) {
        const minimum = this.toNumber(this.minimum());
        const maximum = this.toNumber(this.maximum());

        if (minimum === undefined || maximum === undefined) {
          return 'Enter both minimum and maximum values.';
        }

        if (minimum > maximum) {
          return 'Maximum must be greater than or equal to minimum.';
        }
      }
    }

    if (this.type() === 'CATEGORICAL') {
      const values = this.parseValues();

      if (values.length === 0) {
        return 'Add at least one category value.';
      }

      if (new Set(values).size !== values.length) {
        return 'Category values must be unique.';
      }
    }

    return '';
  }

  save(): void {
    this.showValidation.set(true);

    if (!this.canSave()) {
      return;
    }

    const draft: FieldDraft = {
      name: this.name().trim(),
      type: this.type(),
    };

    if (this.type() === 'IDENTIFIER') {
      draft.identity = {
        strategy: 'SEQUENTIAL_ID',
      };
    } else {
      draft.generation = this.buildGeneration();
    }

    this.saved.emit(draft);
  }

  close(): void {
    this.closed.emit();
  }

  handleTypeChanged(value: FieldType): void {
    this.type.set(value);
    this.distribution.set('');
    this.generator.set('');
  }

  handleAiGenerate(): void {
    /*
     * Field-specific AI proposal generation is intentionally not connected
     * until the production backend exposes a field proposal contract.
     */
  }

  regenerateAiProposal(): void {
    // Reserved for the field-specific AI contract.
  }

  useAiProposal(): void {
    // Reserved for the field-specific AI contract.
  }

  private buildGeneration(): FieldDraft['generation'] {
    const generation: NonNullable<FieldDraft['generation']> = {
      strategy: 'RANDOM',
    };

    if (this.type() === 'BOOLEAN') {
      return generation;
    }

    if (this.type() === 'STRING') {
      const parameters: Record<string, unknown> = {};

      generation.generator = this.generator();

      if (this.generator() === 'RANDOM_STRING') {
        parameters['minimum_length'] = this.toInteger(
          this.minimumLength(),
        );
        parameters['maximum_length'] = this.toInteger(
          this.maximumLength(),
        );
        parameters['character_set'] = this.characterSet();
      }

      if (this.generator() === 'PATTERN') {
        parameters['pattern'] = this.pattern().trim();
      }

      if (this.generator() === 'SEMANTIC') {
        parameters['description'] =
          this.semanticDescription().trim();
      }

      if (Object.keys(parameters).length > 0) {
        generation.parameters = parameters;
      }

      return generation;
    }

    if (this.type() === 'CATEGORICAL') {
      generation.distribution = 'CATEGORICAL';
    } else {
      generation.distribution = this.distribution();
    }

    const parameters: Record<string, unknown> = {};

    if (
      this.distribution() === 'UNIFORM' ||
      this.distribution() === 'DISCRETE_UNIFORM'
    ) {
      parameters['minimum'] = this.toNumber(this.minimum());
      parameters['maximum'] = this.toNumber(this.maximum());
    }

    if (this.type() === 'CATEGORICAL') {
      parameters['values'] = this.parseValues();
    }

    if (Object.keys(parameters).length > 0) {
      generation.parameters = parameters;
    }

    return generation;
  }

  previewPattern(pattern: string): string {
    const value = pattern.trim();

    if (!value) {
      return 'Enter a pattern above';
    }

    let seed = 0;

    for (let index = 0; index < value.length; index += 1) {
      seed = (seed * 31 + value.charCodeAt(index)) >>> 0;
    }

    const nextRandom = (): number => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };

    const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const lowercase = 'abcdefghijklmnopqrstuvwxyz';
    const digits = '0123456789';
    const alphanumeric = uppercase + lowercase + digits;

    return Array.from(value)
      .map((character) => {
        if (character === '#') {
          return digits[Math.floor(nextRandom() * digits.length)];
        }

        if (character === 'A') {
          return uppercase[Math.floor(nextRandom() * uppercase.length)];
        }

        if (character === 'a') {
          return lowercase[Math.floor(nextRandom() * lowercase.length)];
        }

        if (character === 'X') {
          return alphanumeric[
            Math.floor(nextRandom() * alphanumeric.length)
          ];
        }

        return character;
      })
      .join('');
  }

  private parseValues(): string[] {
    return this.categoricalValues()
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
  }

  normalizeNumberInput(value: unknown): string {
    return value === null || value === undefined ? '' : String(value);
  }

  private toInteger(value: string): number | undefined {
    if (!value.trim()) {
      return undefined;
    }

    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  private toNumber(value: string): number | undefined {
    if (!value.trim()) {
      return undefined;
    }

    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  private reset(): void {
    this.showValidation.set(false);
    this.name.set('');
    this.type.set('STRING');
    this.distribution.set('');
    this.generator.set('');
    this.minimum.set('');
    this.maximum.set('');
    this.pattern.set('');
    this.semanticDescription.set('');
    this.characterSet.set('ALPHANUMERIC');
    this.minimumLength.set('');
    this.maximumLength.set('');
    this.categoricalValues.set('');
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
          this.aiCapabilityMessage.set(
            capability.available
              ? 'Field-specific AI authoring will be enabled when the production field proposal contract is available.'
              : capability.message,
          );
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
}
