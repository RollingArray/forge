/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: model-studio.component.ts
 * Purpose: Defines the production Model Studio screen.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { ForgeSpecification } from '../../core/interfaces/forge-specification.interface';
import { SpecificationService } from '../../core/services/specification.service';

import { adaptSpecification } from './data/specification-adapter';
import { CanvasEntity } from './models/model-studio.models';
import { ModelCanvasComponent } from './components/model-canvas/model-canvas.component';
import { EntityDialogComponent } from './components/entity-dialog/entity-dialog.component';
import { EntityInspectorComponent } from './components/entity-inspector/entity-inspector.component';
import { FieldDialogComponent, FieldDraft } from './components/field-dialog/field-dialog.component';

type StudioStep =
  | 'model'
  | 'validate'
  | 'population'
  | 'generate'
  | 'results';

interface StudioStepItem {
  id: StudioStep;
  number: number;
  label: string;
}

@Component({
  selector: 'app-model-studio',
  standalone: true,
  imports: [ModelCanvasComponent, EntityDialogComponent, EntityInspectorComponent, FieldDialogComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="model-studio-page">

      <section class="workflow-page-header">

        <div class="workflow-stepper-row">
          <nav
            class="workflow-stepper"
            aria-label="FORGE workflow"
          >
            @for (
              step of steps;
              track step.id;
              let last = $last
            ) {
              <button
                type="button"
                class="step"
                [class.active]="activeStep() === step.id"
                [class.completed]="isCompleted(step.number)"
                (click)="selectStep(step.id)"
              >
                <span class="step-number">
                  @if (isCompleted(step.number)) {
                    <span class="material-symbols-outlined">
                      check
                    </span>
                  } @else {
                    {{ step.number }}
                  }
                </span>

                <span class="step-label">
                  {{ step.label }}
                </span>
              </button>

              @if (!last) {
                <span
                  class="step-chevron material-symbols-outlined"
                  aria-hidden="true"
                >
                  chevron_right
                </span>
              }
            }
          </nav>
        </div>

        <div class="page-identity">

          <div class="identity-main">

            <div class="title-row">
              <span
                class="page-icon material-symbols-outlined"
                aria-hidden="true"
              >
                account_tree
              </span>

              <h1>
                Model Studio
              </h1>
            </div>

            <p>
              Define and review the entities, relationships, and
              constraints that drive synthetic data generation.
            </p>

          </div>

          <div
            class="step-progress"
            aria-label="Workflow progress"
          >
            {{ activeStepNumber() }} of {{ steps.length }} steps
          </div>

        </div>

      </section>

      <main class="model-studio-content">

        @if (errorMessage(); as error) {
          <section class="model-state">
            <span class="material-symbols-outlined">
              error
            </span>

            <h2>
              Unable to load Model Studio
            </h2>

            <p>
              {{ error }}
            </p>
          </section>
        } @else if (specification(); as specification) {

          <section class="model-summary">

            <div>
              <span class="summary-label">
                Data Model
              </span>

              <h2>
                {{ specification.model.name }}
              </h2>

              @if (specification.model.description) {
                <p>
                  {{ specification.model.description }}
                </p>
              }
            </div>

            <div class="summary-actions">
              <div class="summary-metrics">
                <span>
                  <strong>{{ specification.entities.length }}</strong>
                  entities
                </span>

                <span>
                  <strong>{{ specification.relationships.length }}</strong>
                  relationships
                </span>

                <span>
                  <strong>{{ specification.constraints.length }}</strong>
                  constraints
                </span>
              </div>

              <button
                type="button"
                class="primary-action"
                (click)="openEntityDialog()"
              >
                <span class="material-symbols-outlined">
                  add
                </span>

                Add Entity
              </button>
            </div>

          </section>

          <section class="model-workspace">
            <section class="model-canvas-container">
              <app-model-studio-canvas
                [entities]="canvasEntities()"
                [relationships]="modelRelationships()"
                [selectedEntity]="selectedEntity()"
                (entitySelected)="selectedEntity.set($event)"
              />

              @if (specification.entities.length === 0) {
                <div class="canvas-empty-state">
                  <span class="material-symbols-outlined">
                    account_tree
                  </span>

                  <h2>
                    Start building your model
                  </h2>

                  <p>
                    This Data Model does not have any entities yet.
                  </p>

                </div>
              }
            </section>

            @if (selectedEntityData(); as entity) {
              <app-model-studio-entity-inspector
                [entity]="entity"
                (addField)="openFieldDialog()"
                (closed)="selectedEntity.set('')"
              />
            }
          </section>

        } @else {
          <section class="model-state">
            <span class="material-symbols-outlined">
              account_tree
            </span>

            <h2>
              Loading Model Studio
            </h2>

            <p>
              Loading the Data Model specification.
            </p>
          </section>
        }

      </main>

      @if (entityDialogOpen()) {
        <app-model-studio-entity-dialog
          (saved)="handleEntityCreated($event)"
          (closed)="closeEntityDialog()"
        />
      }

      @if (fieldDialogOpen()) {
        <app-model-studio-field-dialog
          (saved)="handleFieldCreated($event)"
          (closed)="closeFieldDialog()"
        />
      }

    </section>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
      overflow: hidden;
      background: #ffffff;
    }

    .model-studio-page {
      display: flex;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
      flex-direction: column;
      overflow: hidden;
      background: #ffffff;
    }

    .workflow-page-header {
      display: flex;
      flex-direction: column;
      flex: 0 0 auto;
      border-bottom: 1px solid #e7e9f0;
      background: #ffffff;
    }

    .workflow-stepper-row {
      display: flex;
      min-height: 62px;
      align-items: center;
      padding: 0 16px;
      border-bottom: 1px solid #eef0f5;
    }

    .workflow-stepper {
      display: inline-flex;
      height: 38px;
      align-items: center;
      padding: 0 7px;
      border: 1px solid #e1e4ec;
      border-radius: 9px;
      background: #ffffff;
    }

    .step {
      display: inline-flex;
      height: 30px;
      align-items: center;
      gap: 8px;
      padding: 0 7px;
      border: 0;
      border-radius: 7px;
      background: transparent;
      color: #8a92aa;
      font-family: inherit;
      font-size: 12px;
      cursor: pointer;
    }

    .step:hover {
      color: #4d46c5;
      background: #faf9ff;
    }

    .step-number {
      display: grid;
      width: 21px;
      height: 21px;
      place-items: center;
      border-radius: 50%;
      background: #e7e9ef;
      color: #66708e;
      font-size: 11px;
      font-weight: 600;
    }

    .step.active {
      color: #453dcc;
      background: #f3f1ff;
    }

    .step.active .step-number {
      background: #5b53dc;
      color: #ffffff;
    }

    .step.completed {
      color: #566078;
    }

    .step.completed .step-number {
      background: #e7f6ef;
      color: #14945d;
    }

    .step-chevron {
      color: #b0b5c4;
      font-size: 15px;
    }

    .page-identity {
      display: flex;
      min-height: 88px;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      padding: 16px 24px;
    }

    .identity-main {
      min-width: 0;
    }

    .title-row {
      display: flex;
      align-items: center;
      gap: 9px;
    }

    .page-icon {
      flex: 0 0 auto;
      color: #554dd4;
      font-size: 25px;
    }

    .page-identity h1 {
      margin: 0;
      color: #171c38;
      font-size: 20px;
      font-weight: 650;
      line-height: 1.25;
    }

    .page-identity p {
      max-width: 850px;
      margin: 5px 0 0;
      color: #737a8e;
      font-size: 12px;
      line-height: 1.5;
    }

    .step-progress {
      flex: 0 0 auto;
      padding: 6px 10px;
      border: 1px solid #dedcf4;
      border-radius: 7px;
      background: #f7f6ff;
      color: #554dd4;
      font-size: 11px;
      font-weight: 650;
      white-space: nowrap;
    }

    .model-studio-content {
      display: flex;
      min-width: 0;
      min-height: 0;
      flex: 1;
      flex-direction: column;
      gap: 16px;
      overflow: hidden;
      padding: 20px 24px 24px;
      background: #f8f9fc;
    }

    .model-summary {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      padding: 20px;
      border: 1px solid #e5e7ee;
      border-radius: 10px;
      background: #ffffff;
    }

    .summary-label {
      color: #858ca1;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .model-summary h2,
    .entity-preview h2 {
      margin: 4px 0 0;
      color: #171c38;
      font-size: 18px;
      font-weight: 650;
    }

    .model-summary p {
      margin: 5px 0 0;
      color: #737a8e;
      font-size: 12px;
    }

    .summary-actions {
      display: flex;
      align-items: center;
      gap: 20px;
    }

    .summary-metrics {
      display: flex;
      align-items: center;
      gap: 20px;
      color: #737a8e;
      font-size: 12px;
      white-space: nowrap;
    }

    .summary-metrics strong {
      color: #171c38;
      font-size: 16px;
    }

    .model-state {
      display: flex;
      min-height: 280px;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px;
      border: 1px dashed #d9dce7;
      border-radius: 10px;
      background: #ffffff;
      text-align: center;
    }

    .model-state > .material-symbols-outlined {
      margin-bottom: 10px;
      color: #554dd4;
      font-size: 34px;
    }

    .model-state h2 {
      margin: 0;
      color: #171c38;
      font-size: 18px;
      font-weight: 650;
    }

    .model-state p {
      max-width: 440px;
      margin: 7px 0 18px;
      color: #737a8e;
      font-size: 12px;
      line-height: 1.5;
    }

    .primary-action {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 8px 13px;
      border: 0;
      border-radius: 7px;
      background: #554dd4;
      color: #ffffff;
      font-family: inherit;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }

    .primary-action .material-symbols-outlined {
      font-size: 17px;
    }

    .model-workspace {
      display: flex;
      min-width: 0;
      min-height: 0;
      flex: 1;
      gap: 12px;
      overflow: hidden;
    }

    .model-canvas-container {
      position: relative;
      display: flex;
      min-width: 0;
      min-height: 0;
      flex: 1;
      overflow: hidden;
      border: 1px solid #e5e7ee;
      border-radius: 10px;
      background: #f7f8fc;
    }

    .canvas-empty-state {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      pointer-events: none;
      text-align: center;
    }

    .canvas-empty-state > .material-symbols-outlined {
      margin-bottom: 10px;
      color: #554dd4;
      font-size: 34px;
    }

    .canvas-empty-state h2 {
      margin: 0;
      color: #171c38;
      font-size: 18px;
      font-weight: 650;
    }

    .canvas-empty-state p {
      max-width: 440px;
      margin: 7px 0 18px;
      color: #737a8e;
      font-size: 12px;
      line-height: 1.5;
    }

    .canvas-empty-state .primary-action {
      pointer-events: auto;
    }

    app-model-studio-canvas {
      display: block;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
    }

    @media (max-width: 760px) {
      .workflow-stepper-row {
        overflow-x: auto;
      }

      .workflow-stepper {
        flex: 0 0 auto;
      }

      .page-identity {
        align-items: flex-start;
        flex-direction: column;
        padding: 14px 16px;
      }

      .step-progress {
        align-self: flex-start;
      }

      .model-summary {
        align-items: flex-start;
        flex-direction: column;
      }

      .summary-metrics {
        flex-wrap: wrap;
        white-space: normal;
      }
    }
  `],
})
export class ModelStudioComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly specificationService = inject(SpecificationService);

  readonly specification =
    signal<ForgeSpecification | null>(null);

  readonly canvasEntities =
    signal<CanvasEntity[]>([]);

  readonly modelRelationships =
    signal<ReturnType<typeof adaptSpecification>['relationships']>([]);

  readonly selectedEntity =
    signal('');

  readonly selectedEntityData = () =>
    this.specification()?.entities.find(
      (entity) => entity.name === this.selectedEntity(),
    ) ?? null;

  readonly entityDialogOpen =
    signal(false);

  readonly fieldDialogOpen =
    signal(false);
  readonly errorMessage = signal<string | null>(null);

  readonly steps: readonly StudioStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];

  readonly activeStep = signal<StudioStep>('model');

  readonly activeStepNumber = () =>
    this.steps.find(
      (step) => step.id === this.activeStep(),
    )?.number ?? 1;

  constructor() {
    const dataModelId =
      this.route.snapshot.paramMap.get('dataModelId');

    if (!dataModelId) {
      this.errorMessage.set(
        'Data Model ID is missing from the route.',
      );
      return;
    }

    this.loadSpecification(dataModelId);
  }

  isCompleted(stepNumber: number): boolean {
    return stepNumber < this.activeStepNumber();
  }

  selectStep(step: StudioStep): void {
    this.activeStep.set(step);
  }

  private loadSpecification(dataModelId: string): void {
    this.specificationService
      .getSpecification(dataModelId)
      .subscribe({
        next: (specification) => {
          this.specification.set(specification);

          const modelStudioData =
            adaptSpecification(specification);

          this.canvasEntities.set(
            modelStudioData.entities,
          );

          this.modelRelationships.set(
            modelStudioData.relationships,
          );

          this.errorMessage.set(null);
        },
        error: (error) => {
          console.error(
            '[FORGE Model Studio] Failed to load specification:',
            error,
          );

          this.specification.set(null);
          this.errorMessage.set(
            'Unable to load the Data Model specification.',
          );
        },
      });
  }

  openEntityDialog(): void {
    this.entityDialogOpen.set(true);
  }

  closeEntityDialog(): void {
    this.entityDialogOpen.set(false);
  }

  openFieldDialog(): void {
    if (!this.selectedEntity()) {
      return;
    }

    this.fieldDialogOpen.set(true);
  }

  closeFieldDialog(): void {
    this.fieldDialogOpen.set(false);
  }

  handleFieldCreated(draft: FieldDraft): void {
    const dataModelId =
      this.route.snapshot.paramMap.get('dataModelId');

    const entityName = this.selectedEntity();

    if (!dataModelId || !entityName) {
      this.errorMessage.set(
        'Data Model ID or selected entity is missing.',
      );
      return;
    }

    this.specificationService
      .createField(
        dataModelId,
        entityName,
        draft.name,
        draft.type,
        {
          identity: draft.identity,
          generation: draft.generation,
        },
      )
      .subscribe({
        next: () => {
          this.closeFieldDialog();
          this.loadSpecification(dataModelId);
        },
        error: (error: { error?: { detail?: string } }) => {
          this.errorMessage.set(
            error.error?.detail ??
            'Unable to add the field.',
          );
        },
      });
  }

  handleEntityCreated(entity: {
    name: string;
    description: string;
    population: number;
  }): void {
    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');

    if (!dataModelId) {
      this.errorMessage.set('Data Model ID is missing.');
      return;
    }

    this.specificationService
      .createEntity(dataModelId, entity.name, entity.population)
      .subscribe({
        next: () => {
          this.entityDialogOpen.set(false);
          this.loadSpecification(dataModelId);
        },
        error: (error: { error?: { detail?: string } }) => {
          this.errorMessage.set(
            error.error?.detail ?? 'Failed to create entity.',
          );
        },
      });
  }
}

