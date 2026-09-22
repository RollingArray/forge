import {
  ChangeDetectionStrategy,
  Component,
  computed,
  signal,
} from '@angular/core';

import { SidebarComponent } from '../home/components/sidebar/sidebar.component';

import { StudioHeaderComponent } from './components/studio-header/studio-header.component';
import { WorkflowStepperComponent } from './components/workflow-stepper/workflow-stepper.component';
import { StudioActionsComponent } from './components/studio-actions/studio-actions.component';
import { ModelToolbarComponent } from './components/model-toolbar/model-toolbar.component';
import { ModelCanvasComponent } from './components/model-canvas/model-canvas.component';
import { EntityInspectorComponent } from './components/entity-inspector/entity-inspector.component';

import {
  CanvasEntity,
  EntityAccent,
  ForgeSpecification,
  ModelConstraint,
  ModelField,
  ModelRelationship,
  StudioStep,
} from './models/model-studio.models';

import { adaptSpecification } from './data/specification-adapter';

@Component({
  selector: 'app-model-studio',
  standalone: true,
  imports: [
    SidebarComponent,
    StudioHeaderComponent,
    WorkflowStepperComponent,
    StudioActionsComponent,
    ModelToolbarComponent,
    ModelCanvasComponent,
    EntityInspectorComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './model-studio.component.html',
  styleUrl: './model-studio.component.css',
})
export class ModelStudioComponent {
  readonly steps = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ] as const;

  readonly activeStep = signal<StudioStep>('model');

  readonly entities = signal<CanvasEntity[]>([]);
  readonly relationships = signal<ModelRelationship[]>([]);
  readonly constraints = signal<ModelConstraint[]>([]);

  private readonly workingSpecification =
    signal<ForgeSpecification | null>(null);

  private readonly newEntityNames =
    signal<ReadonlySet<string>>(new Set());

  readonly selectedEntity = signal('');

  readonly selectedEntityData = computed(() =>
    this.entities().find(
      entity => entity.name === this.selectedEntity(),
    ) ?? this.entities()[0],
  );

  constructor() {
    this.loadSpecification();
  }

  private async loadSpecification(): Promise<void> {
    try {
      const response = await fetch('/specification.json');

      if (!response.ok) {
        throw new Error(
          `Unable to load specification: ${response.status}`,
        );
      }

      const specification =
        (await response.json()) as ForgeSpecification;

      this.workingSpecification.set(specification);

      const data = adaptSpecification(specification);

      this.entities.set(data.entities);
      this.relationships.set(data.relationships);
      this.constraints.set(data.constraints);

      if (data.entities.length > 0) {
        this.selectedEntity.set(data.entities[0].name);
      }

      console.info(
        '[FORGE Model Studio] specification loaded',
        {
          entities: data.entities.length,
          relationships: data.relationships.length,
          constraints: data.constraints.length,
        },
      );
    } catch (error) {
      console.error(
        '[FORGE Model Studio] specification load failed',
        error,
      );
    }
  }

  selectStep(step: StudioStep): void {
    this.activeStep.set(step);
  }

  handleAction(action: string): void {
    console.info(
      '[FORGE Model Studio] action:',
      action,
    );
  }

  handleCanvasAction(action: string): void {
    if (action === 'add-entity') {
      this.addEntity();
      return;
    }

    console.info(
      '[FORGE Model Studio] canvas action:',
      action,
    );
  }

  handleEntitySelected(entityName: string): void {
    this.selectedEntity.set(entityName);
  }

  private addEntity(): void {
    const specification = this.workingSpecification();

    if (!specification) {
      console.warn(
        '[FORGE Model Studio] Cannot add entity before specification is loaded.',
      );
      return;
    }

    const existingNames = new Set(
      specification.entities.map(entity => entity.name),
    );

    let index = specification.entities.length + 1;
    let entityName = `NEW_ENTITY_${index}`;

    while (existingNames.has(entityName)) {
      index += 1;
      entityName = `NEW_ENTITY_${index}`;
    }

    const newEntity = {
      name: entityName,
      description: 'New entity',
      color: 'blue' as EntityAccent,
      population: {
        count: 0,
      },
      fields: [
        {
          name: 'ID',
          type: 'STRING',
          description: 'Entity identifier',
          identity: {
            strategy: 'AUTO_INCREMENT',
          },
        },
      ],
      identity: {
        fields: ['ID'],
      },
    };

    const updatedSpecification: ForgeSpecification = {
      ...specification,
      entities: [
        ...specification.entities,
        newEntity,
      ],
    };

    this.workingSpecification.set(
      updatedSpecification,
    );

    const data =
      adaptSpecification(updatedSpecification);

    const newEntityNames = new Set(
      this.newEntityNames(),
    );

    newEntityNames.add(entityName);
    this.newEntityNames.set(newEntityNames);

    this.entities.set(
      data.entities.map(entity =>
        newEntityNames.has(entity.name)
          ? {
              ...entity,
              isNew: true,
            }
          : entity,
      ),
    );
    this.relationships.set(data.relationships);
    this.constraints.set(data.constraints);

    this.selectedEntity.set(entityName);

    console.info(
      '[FORGE Model Studio] entity added:',
      entityName,
    );
  }

  updateEntity(event: {
    entityName: string;
    description: string;
    accent: EntityAccent;
  }): void {
    this.entities.update(entities =>
      entities.map(entity =>
        entity.name === event.entityName
          ? {
              ...entity,
              description: event.description,
              accent: event.accent,
            }
          : entity,
      ),
    );
  }

  addField(event: {
    entityName: string;
    field: ModelField;
  }): void {
    this.entities.update(entities =>
      entities.map(entity =>
        entity.name === event.entityName
          ? {
              ...entity,
              fields: [...entity.fields, event.field],
            }
          : entity,
      ),
    );
  }

  addRelationship(
    relationship: ModelRelationship,
  ): void {
    this.relationships.update(relationships => [
      ...relationships,
      relationship,
    ]);

    this.entities.update(entities =>
      entities.map(entity => {
        if (entity.name !== relationship.target) {
          return entity;
        }

        return {
          ...entity,
          fields: entity.fields.map(field =>
            relationship.targetFields.includes(field.name)
              ? {
                  ...field,
                  foreignKey: true,
                }
              : field,
          ),
        };
      }),
    );
  }

  addConstraint(
    constraint: ModelConstraint,
  ): void {
    this.constraints.update(constraints => [
      ...constraints,
      constraint,
    ]);
  }
}
