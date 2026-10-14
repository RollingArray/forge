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

import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ForgeConstraint } from '../../core/interfaces/forge-constraint.interface';
import { ForgeSpecification } from '../../core/interfaces/forge-specification.interface';
import { ForgeSpecificationField } from '../../core/interfaces/forge-specification-field.interface';
import { ForgeSpecificationRelationship } from '../../core/interfaces/forge-specification-relationship.interface';
import { ForgeForeignKey } from '../../core/interfaces/forge-foreign-key.interface';
import { SpecificationService } from '../../core/services/specification.service';
import { NotificationService } from '../../core/services/notification.service';
import { ConfirmationDialogComponent } from '../../shared/components/confirmation-dialog/confirmation-dialog.component';
import { AIService } from '../../core/services/ai.service';
import { AIEntityProposal } from '../../core/interfaces/ai-entity-proposal.interface';
import { adaptSpecification } from './data/specification-adapter';
import { CanvasEntity } from './models/model-studio.models';
import { ModelCanvasComponent } from './components/model-canvas/model-canvas.component';
import { EntityDialogComponent } from './components/entity-dialog/entity-dialog.component';
import { EntityInspectorComponent } from './components/entity-inspector/entity-inspector.component';
import { FieldDialogComponent, FieldDraft } from './components/field-dialog/field-dialog.component';
import { IdentityDialogComponent } from './components/identity-dialog/identity-dialog.component';
import {
  ConstraintDialogComponent,
  ConstraintDraft,
} from './components/constraint-dialog/constraint-dialog.component';
import {
  RelationshipDialogComponent,
  RelationshipDraft,
} from './components/relationship-dialog/relationship-dialog.component';
import {
  ForeignKeyDialogComponent,
  ForeignKeyDraft,
} from './components/foreign-key-dialog/foreign-key-dialog.component';
import {
  WorkflowPageComponent,
} from '../../shared/components/workflow-page/workflow-page.component';
import { ModelStudioSummaryComponent } from './components/model-studio-summary/model-studio-summary.component';
import { WorkflowRowComponent } from '../../shared/components/workflow-row/workflow-row.component';
import {
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';


type StudioStep = WorkflowStep;
type StudioStepItem = WorkflowStepItem;

@Component({
  selector: 'app-model-studio',
  standalone: true,
  imports: [
    ModelCanvasComponent,
    EntityDialogComponent,
    EntityInspectorComponent,
    FieldDialogComponent,
    IdentityDialogComponent,
    ConstraintDialogComponent,
    RelationshipDialogComponent,
    ForeignKeyDialogComponent,
    WorkflowPageComponent,
    ModelStudioSummaryComponent,
    WorkflowRowComponent,
    ConfirmationDialogComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './model-studio.component.html',
  styleUrl: './model-studio.component.css',
})
export class ModelStudioComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly specificationService = inject(SpecificationService);
  private readonly notificationService = inject(NotificationService);
  private readonly aiService = inject(AIService);

  readonly specification = signal<ForgeSpecification | null>(null);

  readonly canvasEntities = signal<CanvasEntity[]>([]);

  readonly modelRelationships = signal<ReturnType<typeof adaptSpecification>['relationships']>([]);

  readonly selectedEntity = signal('');

  readonly selectedEntityData = () =>
    this.specification()?.entities.find((entity) => entity.name === this.selectedEntity()) ?? null;

  readonly entityDialogOpen = signal(false);
  readonly entityAiLoading = signal(false);
  readonly entityAiError = signal<string | null>(null);
  readonly entityAiProposal = signal<AIEntityProposal | null>(null);

  readonly fieldDialogOpen = signal(false);

  readonly editingField = signal<ForgeSpecificationField | null>(null);

  readonly identityDialogOpen = signal(false);

  readonly constraintDialogOpen = signal(false);

  readonly editingConstraint =
    signal<ForgeConstraint | null>(null);

  readonly relationshipDialogOpen = signal(false);

  readonly foreignKeyDialogOpen = signal(false);

  readonly editingForeignKey = signal<ForgeForeignKey | null>(null);

  readonly editingRelationship = signal<ForgeSpecificationRelationship | null>(null);
  readonly relationshipPendingDeletion = signal<ForgeSpecificationRelationship | null>(null);
  readonly relationshipDeleteBusy = signal(false);
  readonly constraintDeleteBusy = signal(false);

  readonly relationshipSourceEntity = signal('');

  readonly foreignKeySourceEntity = signal('');

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
    this.steps.find((step) => step.id === this.activeStep())?.number ?? 1;

  constructor() {
    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');

    if (!dataModelId) {
      this.errorMessage.set('Data Model ID is missing from the route.');
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
    this.specificationService.getSpecification(dataModelId).subscribe({
      next: (specification) => {
        this.specification.set(specification);

        const modelStudioData = adaptSpecification(specification);

        this.canvasEntities.set(modelStudioData.entities);

        this.modelRelationships.set(modelStudioData.relationships);

        this.errorMessage.set(null);
      },
      error: (error) => {
        console.error('[FORGE Model Studio] Failed to load specification:', error);

        this.specification.set(null);
        this.errorMessage.set('Unable to load the Data Model specification.');
      },
    });
  }

  openEntityDialog(): void {
    this.entityAiLoading.set(false);
    this.entityAiError.set(null);
    this.entityAiProposal.set(null);
    this.entityDialogOpen.set(true);
  }

  requestEntityAiProposal(prompt: string): void {
    if (this.entityAiLoading()) {
      return;
    }

    this.entityAiLoading.set(true);
    this.entityAiError.set(null);
    this.entityAiProposal.set(null);

    this.aiService.proposeEntity(prompt).subscribe({
      next: (proposal) => {
        this.entityAiProposal.set(proposal);
        this.entityAiLoading.set(false);
      },
      error: (error: { error?: { detail?: string } }) => {
        this.entityAiError.set(
          error.error?.detail ?? 'FORGE AI could not generate an entity proposal.',
        );
        this.entityAiLoading.set(false);
      },
    });
  }

  closeEntityDialog(): void {
    this.entityDialogOpen.set(false);
    this.entityAiLoading.set(false);
    this.entityAiError.set(null);
    this.entityAiProposal.set(null);
  }

  openIdentityDialog(): void {
    if (!this.selectedEntity()) {
      return;
    }

    this.identityDialogOpen.set(true);
  }

  closeIdentityDialog(): void {
    this.identityDialogOpen.set(false);
  }

  openConstraintDialog(): void {
    if (!this.selectedEntity() || !this.specification()) {
      return;
    }

    this.editingConstraint.set(null);
    this.constraintDialogOpen.set(true);
  }

  openConstraintEditDialog(constraint: ForgeConstraint): void {
    if (!this.specification()) {
      return;
    }

    this.editingConstraint.set(constraint);
    this.constraintDialogOpen.set(true);
  }

  closeConstraintDialog(): void {
    this.constraintDialogOpen.set(false);
    this.editingConstraint.set(null);
  }

  handleConstraintSaved(draft: ConstraintDraft): void {
    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');

    if (!dataModelId) {
      this.errorMessage.set('Data Model ID is missing from the route.');
      return;
    }

    const existingConstraint = this.editingConstraint();

    if (existingConstraint) {
      this.specificationService
        .updateConstraint(dataModelId, {
          existing: existingConstraint,
          constraint: draft,
        })
        .subscribe({
          next: () => {
            this.notificationService.success(
              'Constraint updated',
              'The constraint was updated successfully.',
            );
            this.closeConstraintDialog();
            this.loadSpecification(dataModelId);
          },
          error: (error: { error?: { detail?: string } }) => {
            this.errorMessage.set(
              error.error?.detail ?? 'Unable to update the constraint.',
            );
          },
        });

      return;
    }

    this.specificationService
      .createConstraint(dataModelId, draft)
      .subscribe({
        next: () => {
          this.notificationService.success(
            'Constraint added',
            'The constraint was added successfully.',
          );
          this.closeConstraintDialog();
          this.loadSpecification(dataModelId);
        },
        error: (error: { error?: { detail?: string } }) => {
          this.errorMessage.set(
            error.error?.detail ?? 'Unable to add the constraint.',
          );
        },
      });
  }

  requestConstraintDelete(): void {
    if (!this.editingConstraint() || this.constraintDeleteBusy()) {
      return;
    }

    this.errorMessage.set(null);
    this.confirmConstraintDelete();
  }

  confirmConstraintDelete(): void {
    const constraint = this.editingConstraint();

    if (!constraint || this.constraintDeleteBusy()) {
      return;
    }

    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');
    if (!dataModelId) {
      this.errorMessage.set('Data Model ID is missing from the route.');
      return;
    }

    this.constraintDeleteBusy.set(true);
    this.errorMessage.set(null);

    this.specificationService.deleteConstraint(dataModelId, constraint).subscribe({
      next: () => {
        this.constraintDeleteBusy.set(false);
        this.notificationService.success(
          'Constraint deleted',
          'The constraint was deleted successfully.',
        );
        this.closeConstraintDialog();
        this.loadSpecification(dataModelId);
      },
      error: (error: { error?: { detail?: string } }) => {
        console.error('[FORGE Model Studio] Failed to delete constraint:', error);
        this.constraintDeleteBusy.set(false);
        this.errorMessage.set(
          error.error?.detail ?? 'Unable to delete the constraint.',
        );
      },
    });
  }

  openForeignKeyDialog(sourceEntity?: string): void {
    if (!this.specification()) {
      return;
    }

    this.editingForeignKey.set(null);
    this.foreignKeySourceEntity.set(sourceEntity ?? '');
    this.foreignKeyDialogOpen.set(true);
  }

  openForeignKeyEditDialog(foreignKey: ForgeForeignKey): void {
    if (!this.specification()) {
      return;
    }

    this.errorMessage.set(null);
    this.editingForeignKey.set(foreignKey);
    this.foreignKeySourceEntity.set('');
    this.foreignKeyDialogOpen.set(true);
  }

  closeForeignKeyDialog(): void {
    this.foreignKeyDialogOpen.set(false);
    this.foreignKeySourceEntity.set('');
    this.editingForeignKey.set(null);
  }

  handleForeignKeySaved(draft: ForeignKeyDraft): void {
    const dataModelId =
      this.route.snapshot.paramMap.get('dataModelId');

    if (!dataModelId) {
      this.errorMessage.set(
        'Data Model ID is missing from the route.',
      );
      return;
    }

    const existing = this.editingForeignKey();
    const request = {
      source_entity: draft.sourceEntity,
      source_fields: draft.sourceFields,
      target_entity: draft.targetEntity,
    };

    const operation = existing
      ? this.specificationService.updateForeignKey(dataModelId, {
          existing: { name: existing.name },
          foreign_key: request,
        })
      : this.specificationService.createForeignKey(dataModelId, request);

    operation.subscribe({
      next: () => {
        this.closeForeignKeyDialog();
        this.loadSpecification(dataModelId);
      },
      error: (error: { error?: { detail?: string } }) => {
        this.errorMessage.set(
          error.error?.detail ??
            (existing
              ? 'Unable to update the foreign key.'
              : 'Unable to add the foreign key.'),
        );
      },
    });
  }

  openRelationshipDialog(sourceEntity?: string): void {
    if (!this.specification()) {
      return;
    }

    this.editingRelationship.set(null);
    this.relationshipSourceEntity.set(sourceEntity ?? '');
    this.relationshipDialogOpen.set(true);
  }

  requestRelationshipDelete(relationship: ForgeSpecificationRelationship): void {
    this.relationshipPendingDeletion.set(relationship);
    this.errorMessage.set(null);
    this.confirmRelationshipDelete();
  }

  cancelRelationshipDelete(): void {
    if (!this.relationshipDeleteBusy()) {
      this.relationshipPendingDeletion.set(null);
    }
  }

  confirmRelationshipDelete(): void {
    const relationship = this.relationshipPendingDeletion();

    if (!relationship || this.relationshipDeleteBusy()) {
      return;
    }

    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');
    if (!dataModelId) {
      this.errorMessage.set('Data Model ID is missing from the route.');
      return;
    }

    this.relationshipDeleteBusy.set(true);

    this.specificationService.deleteRelationship(dataModelId, {
      source: relationship.source,
      target: relationship.target,
      type: relationship.type as
        | 'ONE_TO_ONE'
        | 'ONE_TO_MANY'
        | 'MANY_TO_ONE'
        | 'MANY_TO_MANY',
      source_participation: (relationship.source_participation ?? 'MANDATORY') as
        | 'MANDATORY'
        | 'OPTIONAL',
      target_participation: (relationship.target_participation ?? 'MANDATORY') as
        | 'MANDATORY'
        | 'OPTIONAL',
    }).subscribe({
      next: () => {
        this.relationshipDeleteBusy.set(false);
        this.relationshipPendingDeletion.set(null);
        this.notificationService.success(
          'Relationship deleted',
          'The relationship was deleted successfully.',
        );
        this.closeRelationshipDialog();
        this.loadSpecification(dataModelId);
      },
      error: (error: { error?: { detail?: string } }) => {
        console.error('[FORGE Model Studio] Failed to delete relationship:', error);
        this.relationshipDeleteBusy.set(false);
        this.errorMessage.set(
          error.error?.detail ?? 'Unable to delete the relationship.',
        );
      },
    });
  }

  openRelationshipEditDialog(relationship: ForgeSpecificationRelationship): void {
    if (!this.specification()) {
      return;
    }

    this.editingRelationship.set(relationship);
    this.relationshipSourceEntity.set('');
    this.relationshipDialogOpen.set(true);
  }

  closeRelationshipDialog(): void {
    this.relationshipDialogOpen.set(false);
    this.editingRelationship.set(null);
    this.relationshipSourceEntity.set('');
  }

  handleRelationshipSaved(draft: RelationshipDraft): void {
    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');

    if (!dataModelId) {
      this.errorMessage.set('Data Model ID is missing from the route.');
      return;
    }

    const existing = this.editingRelationship();

    if (existing) {
      this.specificationService
        .updateRelationship(dataModelId, {
          existing: {
            source: existing.source,
            target: existing.target,
            type: existing.type as 'ONE_TO_ONE' | 'ONE_TO_MANY' | 'MANY_TO_ONE' | 'MANY_TO_MANY',
            source_participation: (existing.source_participation ?? 'MANDATORY') as
              'MANDATORY' | 'OPTIONAL',
            target_participation: (existing.target_participation ?? 'MANDATORY') as
              'MANDATORY' | 'OPTIONAL',
          },
          relationship: {
            source_entity: draft.sourceEntity,
            target_entity: draft.targetEntity,
            type: draft.type,
            source_participation: draft.sourceParticipation,
            target_participation: draft.targetParticipation,
          },
        })
        .subscribe({
          next: () => {
            this.closeRelationshipDialog();
            this.loadSpecification(dataModelId);
          },
          error: (error: { error?: { detail?: string } }) => {
            this.errorMessage.set(error.error?.detail ?? 'Unable to update the relationship.');
          },
        });

      return;
    }

    this.specificationService
      .createRelationship(dataModelId, {
        source_entity: draft.sourceEntity,
        target_entity: draft.targetEntity,
        type: draft.type,
        source_participation: draft.sourceParticipation,
        target_participation: draft.targetParticipation,
      })
      .subscribe({
        next: () => {
          this.closeRelationshipDialog();
          this.loadSpecification(dataModelId);
        },
        error: (error: { error?: { detail?: string } }) => {
          this.errorMessage.set(error.error?.detail ?? 'Unable to create the relationship.');
        },
      });
  }

  handleIdentitySaved(fields: string[]): void {
    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');

    const entityName = this.selectedEntity();

    if (!dataModelId || !entityName) {
      this.errorMessage.set('Data Model ID or selected entity is missing.');
      return;
    }

    this.specificationService.updateEntityIdentity(dataModelId, entityName, fields).subscribe({
      next: () => {
        this.closeIdentityDialog();
        this.loadSpecification(dataModelId);
      },
      error: (error: { error?: { detail?: string } }) => {
        this.errorMessage.set(error.error?.detail ?? 'Unable to update the entity identity.');
      },
    });
  }

  openFieldDialog(): void {
    if (!this.selectedEntity()) {
      return;
    }

    this.editingField.set(null);
    this.fieldDialogOpen.set(true);
  }

  openFieldEditDialog(field: ForgeSpecificationField): void {
    if (!this.selectedEntity()) {
      return;
    }

    this.editingField.set(field);
    this.fieldDialogOpen.set(true);
  }

  closeFieldDialog(): void {
    this.fieldDialogOpen.set(false);
    this.editingField.set(null);
  }

  handleFieldSaved(draft: FieldDraft): void {
    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');

    const entityName = this.selectedEntity();
    const existingField = this.editingField();

    if (!dataModelId || !entityName) {
      this.errorMessage.set('Data Model ID or selected entity is missing.');
      return;
    }

    if (existingField) {
      this.specificationService
        .updateField(dataModelId, entityName, existingField.name, {
          name: draft.name,
          type: draft.type,
          identity: draft.identity,
          generation: draft.generation,
        })
        .subscribe({
          next: () => {
            this.closeFieldDialog();
            this.loadSpecification(dataModelId);
          },
          error: (error: { error?: { detail?: string } }) => {
            this.errorMessage.set(error.error?.detail ?? 'Unable to update the field.');
          },
        });

      return;
    }

    this.specificationService
      .createField(dataModelId, entityName, draft.name, draft.type, {
        identity: draft.identity,
        generation: draft.generation,
      })
      .subscribe({
        next: () => {
          this.closeFieldDialog();
          this.loadSpecification(dataModelId);
        },
        error: (error: { error?: { detail?: string } }) => {
          this.errorMessage.set(error.error?.detail ?? 'Unable to add the field.');
        },
      });
  }

  handleEntityCreated(entity: {
    name: string;
    description: string;
    population: number;
    scaling: 'FIXED' | 'SCALABLE';
  }): void {
    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');

    if (!dataModelId) {
      this.errorMessage.set('Data Model ID is missing.');
      return;
    }

    this.specificationService
      .createEntity(
        dataModelId,
        entity.name,
        entity.population,
        entity.scaling,
      )
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
  continueToValidation(): void {
    const dataModelId = this.route.snapshot.paramMap.get('dataModelId');

    if (!dataModelId || (this.specification()?.entities?.length ?? 0) === 0) {
      return;
    }

    void this.router.navigate([
      '/workspace',
      dataModelId,
      'model-validation',
    ]);
  }

}
