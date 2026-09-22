import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  signal,
} from '@angular/core';

import {
  CanvasEntity,
  ModelField,
} from '../../models/model-studio.models';

@Component({
  selector: 'app-entity-editor',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './entity-editor.component.html',
  styleUrl: './entity-editor.component.css',
})
export class EntityEditorComponent {
  readonly entity = input.required<CanvasEntity>();

  readonly saved = output<CanvasEntity>();
  readonly cancelled = output<void>();

  readonly entityName = signal('');
  readonly description = signal('');
  readonly fields = signal<ModelField[]>([]);

  ngOnInit(): void {
    const entity = this.entity();

    this.entityName.set(entity.name);
    this.description.set(entity.description);
    this.fields.set(
      entity.fields.map(field => ({ ...field })),
    );
  }

  updateName(value: string): void {
    this.entityName.set(value);
  }

  updateDescription(value: string): void {
    this.description.set(value);
  }

  updateFieldName(index: number, value: string): void {
    this.fields.update(fields =>
      fields.map((field, fieldIndex) =>
        fieldIndex === index
          ? { ...field, name: value }
          : field,
      ),
    );
  }

  updateFieldType(index: number, value: string): void {
    this.fields.update(fields =>
      fields.map((field, fieldIndex) =>
        fieldIndex === index
          ? { ...field, type: value }
          : field,
      ),
    );
  }

  toggleNullable(index: number): void {
    this.fields.update(fields =>
      fields.map((field, fieldIndex) =>
        fieldIndex === index
          ? {
              ...field,
              nullable: !field.nullable,
            }
          : field,
      ),
    );
  }

  save(): void {
    this.saved.emit({
      ...this.entity(),
      name: this.entityName().trim(),
      description: this.description().trim(),
      fields: this.fields(),
    });
  }
}
