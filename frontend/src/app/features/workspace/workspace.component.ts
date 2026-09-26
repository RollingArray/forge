/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: workspace.component.ts
 * Purpose: Defines the FORGE Workspace screen and coordinates Workspace actions.
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
import { Router } from '@angular/router';

import { Activity } from '../../core/interfaces/activity.interface';
import { DataModel } from '../../core/interfaces/data-model.interface';
import { Metric } from '../../core/interfaces/metric.interface';
import { Template } from '../../core/interfaces/template.interface';

import { WorkspaceService } from '../../core/services/workspace.service';

import {
  DataModelDialogComponent,
} from './components/data-model-dialog/data-model-dialog.component';
import {
  WorkspaceWelcomeHeaderComponent,
} from './components/workspace-welcome-header/workspace-welcome-header.component';
import {
  WorkspaceContentComponent,
} from './components/workspace-content/workspace-content.component';
import {
  WorkspaceRightRailComponent,
} from './components/workspace-right-rail/workspace-right-rail.component';
import {
  TemplatesComponent as WorkspaceTemplatesComponent,
} from './components/templates/templates.component';
import {
  DataModelShareDialogComponent,
} from './components/data-model-share-dialog/data-model-share-dialog.component';

@Component({
  selector: 'app-workspace',
  standalone: true,
  imports: [
    DataModelDialogComponent,
    WorkspaceWelcomeHeaderComponent,
    WorkspaceContentComponent,
    WorkspaceRightRailComponent,
    WorkspaceTemplatesComponent,
    DataModelShareDialogComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './workspace.component.html',
  styleUrl: './workspace.component.css',
})
export class WorkspaceComponent {
  private readonly router = inject(Router);
  private readonly workspaceService = inject(WorkspaceService);

  readonly metrics = signal<Metric[]>([]);
  readonly dataModels = signal<DataModel[]>([]);
  readonly templates = signal<Template[]>([]);
  readonly activities = signal<Activity[]>([]);

  readonly selectedDataModel = signal<DataModel | null>(null);
  readonly dataModelDialogOpen = signal(false);
  readonly editingDataModel = signal<DataModel | null>(null);
  readonly sharingDataModel = signal<DataModel | null>(null);
  readonly dataModelShareDialogOpen = signal(false);
  readonly savingDataModel = signal(false);

  constructor() {
    this.loadWorkspace();
  }

  loadWorkspace(): void {
    this.workspaceService.loadWorkspace().subscribe({
      next: (workspace) => {
        this.metrics.set(workspace.metrics);
        this.dataModels.set(workspace.dataModels);
        this.templates.set(workspace.templates);
        this.activities.set(workspace.activities);
      },
      error: (error) => {
        console.error(
          '[FORGE Workspace] Failed to load workspace:',
          error,
        );
      },
    });
  }

  handleNewDataModel(): void {
    this.editingDataModel.set(null);
    this.dataModelDialogOpen.set(true);
  }

  handleDataModelSelected(dataModel: DataModel): void {
    void this.router.navigate([
      '/workspace',
      dataModel.dataModelId,
      'model-studio',
    ]);
  }

  handleDataModelEditRequested(dataModel: DataModel): void {
    this.editingDataModel.set(dataModel);
    this.dataModelDialogOpen.set(true);
  }

  handleDataModelShareRequested(dataModel: DataModel): void {
    this.sharingDataModel.set(dataModel);
    this.dataModelShareDialogOpen.set(true);
  }

  closeDataModelShareDialog(): void {
    this.dataModelShareDialogOpen.set(false);
    this.sharingDataModel.set(null);
  }

  handleDataModelSaved(data: {
    name: string;
    description: string;
    color: string;
    tags: string[];
  }): void {
    this.savingDataModel.set(true);

    const editingDataModel = this.editingDataModel();

    const request = {
      name: data.name,
      description: data.description,
      color: data.color,
      tags: data.tags,
    };

    const operation = editingDataModel
      ? this.workspaceService.updateDataModel(
          editingDataModel.dataModelId,
          request,
        )
      : this.workspaceService.createDataModel(request);

    operation.subscribe({
      next: () => {
        this.savingDataModel.set(false);
        this.closeDataModelDialog();
        this.loadWorkspace();
      },
      error: (error) => {
        this.savingDataModel.set(false);

        console.error(
          '[FORGE Workspace] Failed to save Data Model:',
          error,
        );
      },
    });
  }

  handleDataModelDeleted(): void {
    const dataModel = this.editingDataModel();

    if (!dataModel) {
      return;
    }

    this.savingDataModel.set(true);

    this.workspaceService
      .deleteDataModel(dataModel.dataModelId)
      .subscribe({
        next: () => {
          this.savingDataModel.set(false);
          this.closeDataModelDialog();
          this.selectedDataModel.set(null);
          this.loadWorkspace();
        },
        error: (error) => {
          this.savingDataModel.set(false);

          console.error(
            '[FORGE Workspace] Failed to delete Data Model:',
            error,
          );
        },
      });
  }

  closeDataModelDialog(): void {
    this.dataModelDialogOpen.set(false);
    this.editingDataModel.set(null);
  }

  handleTemplateSelected(templateName: string): void {
    console.info(
      '[FORGE Workspace] Template selected:',
      templateName,
    );
  }

  handleQuickAction(action: string): void {
    console.info('[FORGE Workspace] Quick action:', action);
  }

  handleViewAllDataModels(): void {
    console.info('[FORGE Workspace] View all Data Models');
  }

  handleViewAllActivity(): void {
    console.info('[FORGE Workspace] View all activity');
  }

  handleDocumentation(): void {
    console.info('[FORGE Workspace] Documentation requested');
  }
}
