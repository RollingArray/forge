import {
  ChangeDetectionStrategy,
  Component,
  TemplateRef,
  signal,
} from '@angular/core';

import { ChartComponent } from '../../shared/components/chart/chart.component';
import { ModelValidationFindingsComponent } from '../model-validation/components/model-validation-findings/model-validation-findings.component';
import { SpecificationValidationResult } from '../../core/interfaces/specification-validation.interface';
import { MetricCardData } from '../../shared/components/metric-grid/metric-card-data';
import { MetricGridComponent } from '../../shared/components/metric-grid/metric-grid.component';
import { StatusCardComponent } from '../../shared/components/status-card/status-card.component';
import { WorkspaceHeaderComponent } from '../../shared/components/workspace-header/workspace-header.component';
import { WorkspaceSectionComponent } from '../../shared/components/workspace-section/workspace-section.component';
import { WorkspaceSimpleTableComponent } from '../../shared/components/workspace-simple-table/workspace-simple-table.component';
import {
  WorkspaceTableToolbarComponent,
  WorkspaceToolbarAction,
} from '../../shared/components/workspace-table-toolbar/workspace-table-toolbar.component';
import {
  WorkspaceSimpleTableColumn,
} from '../../shared/components/workspace-simple-table/workspace-simple-table.models';
import { WorkflowPageComponent } from '../../shared/components/workflow-page/workflow-page.component';
import { WorkflowRowComponent } from '../../shared/components/workflow-row/workflow-row.component';
import {
  WorkflowStep,
  WorkflowStepItem,
} from '../../shared/components/workflow-stepper/workflow-stepper.component';

interface DesignSystemWideTableRow {
  entity: string;
  records: number;
  errors: number;
  warnings: number;
  relationships: number;
  population: number;
  status: 'valid' | 'warning' | 'error';
}

interface DesignSystemTableRow {
  entity: string;
  records: number;
  errors: number;
  warnings: number;
  status: 'valid' | 'warning' | 'error';
}

@Component({
  selector: 'app-ui-kit-design-system',
  standalone: true,
  imports: [
    WorkflowPageComponent,
    WorkflowRowComponent,
    WorkspaceSectionComponent,
    WorkspaceHeaderComponent,
    MetricGridComponent,
    StatusCardComponent,
    ChartComponent,
    ModelValidationFindingsComponent,
    WorkspaceTableToolbarComponent,
    WorkspaceSimpleTableComponent,
  ],
  templateUrl: './ui-kit-design-system.component.html',
  styleUrl: './ui-kit-design-system.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UiKitDesignSystemComponent {
  readonly steps: readonly WorkflowStepItem[] = [
    { id: 'model', number: 1, label: 'Model' },
    { id: 'validate', number: 2, label: 'Validate' },
    { id: 'population', number: 3, label: 'Population' },
    { id: 'generate', number: 4, label: 'Generate' },
    { id: 'results', number: 5, label: 'Results' },
  ];

  readonly activeStep: WorkflowStep = 'validate';

  readonly metrics: readonly MetricCardData[] = [
    {
      label: 'Entities',
      value: '21',
      description: 'Model entities',
      icon: 'account_tree',
    },
    {
      label: 'Fields',
      value: '44',
      description: 'Defined fields',
      icon: 'view_column',
    },
    {
      label: 'Relationships',
      value: '33',
      description: 'Model relationships',
      icon: 'account_tree',
    },
    {
      label: 'Checks',
      value: '126',
      description: 'Deterministic checks',
      icon: 'fact_check',
    },
  ];

  readonly statusChartLabels = [
    'Valid',
    'Warning',
    'Error',
  ];

  readonly statusChartDatasets = [
    {
      data: [112, 9, 5],
    },
  ];


  readonly populationChartLabels = [
    'Customer',
    'Sales Order',
    'Order Item',
    'Delivery',
    'Delivery Item',
    'Invoice',
    'Invoice Item',
    'Payment',
    'Credit Memo',
    'Accounting Document',
    'Material Document',
    'Purchase Order',
    'Purchase Order Item',
    'Goods Receipt',
  ];

  readonly populationChartDatasets = [
    {
      label: 'Population',
      data: [
        5000,
        12000,
        30000,
        9000,
        18000,
        7500,
        15000,
        6200,
        420,
        18000,
        14200,
        6800,
        16400,
        9100,
      ],
    },
  ];

  readonly statusDistributionLabels = [
    'Valid',
    'Warning',
    'Error',
  ];

  readonly statusDistributionDatasets = [
    {
      data: [112, 9, 5],
    },
  ];

  readonly toolbarActions: readonly WorkspaceToolbarAction[] = [
    {
      id: 'refresh',
      icon: 'refresh',
      tooltip: 'Refresh table',
    },
    {
      id: 'export',
      icon: 'download',
      label: 'Export',
      variant: 'primary',
    },
    {
      id: 'delete',
      icon: 'delete',
      label: 'Delete',
      variant: 'danger',
    },
    {
      id: 'settings',
      icon: 'settings',
      label: 'Settings',
      disabled: true,
      tooltip: 'Settings are not available in this demo',
    },
  ];

  readonly toolbarActionMessage = signal(
    'No toolbar action selected.',
  );

  readonly designSystemValidation: SpecificationValidationResult = {
    modelName: 'Design System Validation Example',
    specificationVersion: '1.0.0',
    vocabularyVersion: '1.0',
    errors: 0,
    warnings: 0,
    passed: 0,
    totalChecks: 15,
    entitiesValidated: 6,
    canContinue: false,
    findings: [
      {
        id: 'ds-001',
        severity: 'error',
        category: 'Foreign Key',
        title: 'Foreign key references unknown entity',
        details: 'The configured foreign key points to an entity that does not exist in the specification.',
        entity: 'Sales Order',
        field: 'customer_id',
      },
      {
        id: 'ds-002',
        severity: 'warning',
        category: 'Relationship',
        title: 'Optional relationship has incomplete participation',
        details: 'The relationship allows optional participation and may produce sparse references.',
        entity: 'Delivery',
        field: 'sales_order_id',
      },
      {
        id: 'ds-003',
        severity: 'passed',
        category: 'Entity',
        title: 'Entity definition is valid',
        details: 'All required entity properties and field definitions passed validation.',
        entity: 'Customer',
      },
      {
        id: 'ds-004',
        severity: 'passed',
        category: 'Specification',
        title: 'Specification version is supported',
        details: 'The specification uses a supported specification and vocabulary version.',
      },
      {
        id: 'ds-005',
        severity: 'warning',
        category: 'Constraint',
        title: 'Constraint may reduce feasible population',
        details: 'The configured constraint can restrict the available population range.',
        entity: 'Invoice',
      },
      {
        id: 'ds-006',
        severity: 'error',
        category: 'Relationship',
        title: 'Relationship cardinality is invalid',
        details: 'The configured cardinality is inconsistent with the participating entities.',
        entity: 'Order Item',
      },
      {
        id: 'ds-007',
        severity: 'passed',
        category: 'Foreign Key',
        title: 'Foreign key definition is valid',
        details: 'Referenced entity and field definitions are compatible.',
        entity: 'Delivery Item',
        field: 'delivery_id',
      },
      {
        id: 'ds-008',
        severity: 'warning',
        category: 'Generation',
        title: 'Generation rule uses a broad value range',
        details: 'The configured generation rule may produce a wider value distribution than expected.',
        entity: 'Material',
        field: 'material_group',
      },
      {
        id: 'ds-009',
        severity: 'passed',
        category: 'Relationship',
        title: 'Relationship dependency is valid',
        details: 'The relationship dependency can be resolved during population planning.',
        entity: 'Payment',
      },
      {
        id: 'ds-010',
        severity: 'passed',
        category: 'Model',
        title: 'Model structure is valid',
        details: 'The model contains all required structural definitions.',
      },
      {
        id: 'ds-011',
        severity: 'warning',
        category: 'Entity',
        title: 'Entity contains optional fields',
        details: 'Optional fields may result in partially populated generated records.',
        entity: 'Business Partner',
      },
      {
        id: 'ds-012',
        severity: 'passed',
        category: 'Constraint',
        title: 'Constraint definition is valid',
        details: 'The constraint is structurally valid and can be evaluated deterministically.',
        entity: 'Sales Order',
      },
      {
        id: 'ds-013',
        severity: 'passed',
        category: 'Generation',
        title: 'Generation configuration is valid',
        details: 'Generation configuration contains all required properties.',
        entity: 'Invoice',
      },
      {
        id: 'ds-014',
        severity: 'error',
        category: 'Entity',
        title: 'Required field is missing',
        details: 'A required field referenced by the model is not defined.',
        entity: 'Accounting Document',
        field: 'document_id',
      },
      {
        id: 'ds-015',
        severity: 'passed',
        category: 'Specification',
        title: 'Specification validation completed',
        details: 'All deterministic specification checks completed successfully.',
      },
    ],
    entities: [],
  };


  handleToolbarAction(actionId: string): void {
    const messages: Record<string, string> = {
      refresh: 'Refresh action triggered.',
      export: 'Export action triggered.',
      delete: 'Delete action triggered.',
    };

    this.toolbarActionMessage.set(
      messages[actionId] ?? `Action "${actionId}" triggered.`,
    );
  }

  readonly tableSearch = signal('');

  readonly tableRows: readonly DesignSystemTableRow[] = [
    {
      entity: 'Customer',
      records: 1250,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Sales Order',
      records: 4820,
      errors: 0,
      warnings: 2,
      status: 'warning',
    },
    {
      entity: 'Order Item',
      records: 12450,
      errors: 2,
      warnings: 3,
      status: 'warning',
    },
    {
      entity: 'Invoice',
      records: 980,
      errors: 4,
      warnings: 0,
      status: 'error',
    },
    {
      entity: 'Delivery',
      records: 2760,
      errors: 0,
      warnings: 1,
      status: 'warning',
    },
  ];

  readonly tableRowsValidation: readonly DesignSystemTableRow[] = [
    ...this.tableRows,
    {
      entity: 'Material',
      records: 8320,
      errors: 0,
      warnings: 2,
      status: 'warning',
    },
    {
      entity: 'Plant',
      records: 48,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Storage Location',
      records: 312,
      errors: 1,
      warnings: 0,
      status: 'error',
    },
    {
      entity: 'Business Partner',
      records: 2140,
      errors: 0,
      warnings: 1,
      status: 'warning',
    },
    {
      entity: 'Company Code',
      records: 18,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Sales Organization',
      records: 12,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Distribution Channel',
      records: 9,
      errors: 0,
      warnings: 1,
      status: 'warning',
    },
    {
      entity: 'Billing Document',
      records: 3640,
      errors: 3,
      warnings: 2,
      status: 'error',
    },
  ];

  readonly tableRowsPopulation: readonly DesignSystemTableRow[] = [
    {
      entity: 'Customer',
      records: 5000,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Sales Order',
      records: 12000,
      errors: 0,
      warnings: 2,
      status: 'warning',
    },
    {
      entity: 'Order Item',
      records: 30000,
      errors: 1,
      warnings: 3,
      status: 'warning',
    },
    {
      entity: 'Delivery',
      records: 9000,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Delivery Item',
      records: 18000,
      errors: 0,
      warnings: 1,
      status: 'warning',
    },
    {
      entity: 'Invoice',
      records: 7500,
      errors: 2,
      warnings: 0,
      status: 'error',
    },
    {
      entity: 'Invoice Item',
      records: 15000,
      errors: 0,
      warnings: 2,
      status: 'warning',
    },
    {
      entity: 'Payment',
      records: 6200,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
  ];

  readonly tableRowsGeneration: readonly DesignSystemTableRow[] = [
    {
      entity: 'Customer',
      records: 5000,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Sales Order',
      records: 12000,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Order Item',
      records: 30000,
      errors: 0,
      warnings: 1,
      status: 'warning',
    },
    {
      entity: 'Delivery',
      records: 9000,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Invoice',
      records: 7500,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Payment',
      records: 6200,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
    {
      entity: 'Credit Memo',
      records: 420,
      errors: 0,
      warnings: 1,
      status: 'warning',
    },
    {
      entity: 'Accounting Document',
      records: 18000,
      errors: 0,
      warnings: 0,
      status: 'valid',
    },
  ];

  readonly wideTableColumns: readonly WorkspaceSimpleTableColumn<DesignSystemWideTableRow>[] =
    [
      {
        key: 'entity',
        label: 'Entity',
        width: 'minmax(210px, 2fr)',
      },
      {
        key: 'records',
        label: 'Records',
        type: 'number',
        width: '100px',
        align: 'right',
      },
      {
        key: 'errors',
        label: 'Errors',
        type: 'error-count',
        width: '80px',
        align: 'right',
      },
      {
        key: 'warnings',
        label: 'Warnings',
        type: 'warning-count',
        width: '100px',
        align: 'right',
      },
      {
        key: 'relationships',
        label: 'Relationships',
        type: 'number',
        width: '120px',
        align: 'right',
      },
      {
        key: 'population',
        label: 'Population',
        type: 'number',
        width: '170px',
        align: 'right',
      },
      {
        key: 'status',
        label: 'Status',
        type: 'status',
        width: '110px',
      },
    ];

  readonly wideTableRowsA: DesignSystemWideTableRow[] = [
    { entity: 'Customer', records: 5000, errors: 0, warnings: 0, relationships: 4, population: 5000, status: 'valid' },
    { entity: 'Sales Order', records: 12000, errors: 0, warnings: 2, relationships: 6, population: 12000, status: 'warning' },
    { entity: 'Order Item', records: 30000, errors: 1, warnings: 3, relationships: 5, population: 30000, status: 'warning' },
    { entity: 'Delivery', records: 9000, errors: 0, warnings: 0, relationships: 4, population: 9000, status: 'valid' },
    { entity: 'Delivery Item', records: 18000, errors: 0, warnings: 1, relationships: 3, population: 18000, status: 'warning' },
    { entity: 'Invoice', records: 7500, errors: 2, warnings: 0, relationships: 5, population: 7500, status: 'error' },
    { entity: 'Invoice Item', records: 15000, errors: 0, warnings: 2, relationships: 3, population: 15000, status: 'warning' },
    { entity: 'Payment', records: 6200, errors: 0, warnings: 0, relationships: 3, population: 6200, status: 'valid' },
    { entity: 'Credit Memo', records: 420, errors: 0, warnings: 1, relationships: 2, population: 420, status: 'warning' },
    { entity: 'Accounting Document', records: 18000, errors: 0, warnings: 0, relationships: 5, population: 18000, status: 'valid' },
    { entity: 'Material Document', records: 14200, errors: 1, warnings: 2, relationships: 4, population: 14200, status: 'warning' },
    { entity: 'Purchase Order', records: 6800, errors: 0, warnings: 1, relationships: 4, population: 6800, status: 'warning' },
    { entity: 'Purchase Order Item', records: 16400, errors: 0, warnings: 0, relationships: 3, population: 16400, status: 'valid' },
    { entity: 'Goods Receipt', records: 9100, errors: 1, warnings: 0, relationships: 3, population: 9100, status: 'error' },
  ];

  readonly wideTableRowsB: DesignSystemWideTableRow[] = [
    { entity: 'Material', records: 8320, errors: 0, warnings: 2, relationships: 3, population: 8320, status: 'warning' },
    { entity: 'Plant', records: 48, errors: 0, warnings: 0, relationships: 2, population: 48, status: 'valid' },
    { entity: 'Storage Location', records: 312, errors: 1, warnings: 0, relationships: 2, population: 312, status: 'error' },
    { entity: 'Business Partner', records: 2140, errors: 0, warnings: 1, relationships: 4, population: 2140, status: 'warning' },
    { entity: 'Company Code', records: 18, errors: 0, warnings: 0, relationships: 2, population: 18, status: 'valid' },
    { entity: 'Sales Organization', records: 12, errors: 0, warnings: 0, relationships: 3, population: 12, status: 'valid' },
    { entity: 'Distribution Channel', records: 9, errors: 0, warnings: 1, relationships: 2, population: 9, status: 'warning' },
    { entity: 'Division', records: 6, errors: 0, warnings: 0, relationships: 1, population: 6, status: 'valid' },
    { entity: 'Customer Group', records: 14, errors: 0, warnings: 0, relationships: 2, population: 14, status: 'valid' },
    { entity: 'Material Group', records: 32, errors: 0, warnings: 1, relationships: 2, population: 32, status: 'warning' },
    { entity: 'Shipping Point', records: 26, errors: 0, warnings: 0, relationships: 2, population: 26, status: 'valid' },
    { entity: 'Route', records: 84, errors: 1, warnings: 0, relationships: 3, population: 84, status: 'error' },
    { entity: 'Payment Terms', records: 17, errors: 0, warnings: 0, relationships: 1, population: 17, status: 'valid' },
    { entity: 'Incoterms', records: 11, errors: 0, warnings: 1, relationships: 1, population: 11, status: 'warning' },
  ];

  readonly wideTableColumnsCustom: readonly WorkspaceSimpleTableColumn<DesignSystemWideTableRow>[] = [
    {
      key: 'entity',
      label: 'Entity',
      width: 'minmax(210px, 2fr)',
      template: undefined,
    },
    {
      key: 'records',
      label: 'Records',
      type: 'number',
      align: 'right',
      width: '100px',
    },
    {
      key: 'errors',
      label: 'Errors',
      type: 'error-count',
      align: 'right',
      width: '80px',
    },
    {
      key: 'warnings',
      label: 'Warnings',
      type: 'warning-count',
      align: 'right',
      width: '100px',
    },
    {
      key: 'relationships',
      label: 'Relationships',
      type: 'number',
      align: 'right',
      width: '120px',
    },
    {
      key: 'population',
      label: 'Population',
      align: 'right',
      width: '170px',
      template: undefined,
    },
    {
      key: 'status',
      label: 'Status',
      type: 'status',
      width: '110px',
    },
  ];

  readonly entityDescriptions: Record<string, string> = {
    Customer: 'Business partner master data',
    'Sales Order': 'Order header entity',
    'Order Item': 'Order line-level entity',
    Delivery: 'Outbound logistics document',
    'Delivery Item': 'Delivery line-level entity',
    Invoice: 'Billing document',
    'Invoice Item': 'Billing line-level entity',
    Payment: 'Financial settlement entity',
    'Credit Memo': 'Credit adjustment document',
    'Accounting Document': 'Financial accounting entity',
    'Material Document': 'Inventory movement document',
    'Purchase Order': 'Procurement document',
    'Purchase Order Item': 'Procurement line-level entity',
    'Goods Receipt': 'Inbound inventory movement',
    Material: 'Material master data',
    Plant: 'Operational plant master',
    'Storage Location': 'Inventory storage master',
    'Business Partner': 'Business partner master',
    'Company Code': 'Legal entity master',
    'Sales Organization': 'Sales organizational unit',
    'Distribution Channel': 'Distribution structure',
    Division: 'Product division',
    'Customer Group': 'Customer segmentation',
    'Material Group': 'Material classification',
    'Shipping Point': 'Shipping execution unit',
    Route: 'Transportation route',
    'Payment Terms': 'Payment condition master',
    Incoterms: 'International trade terms',
  };

  readonly maxPopulation = 30000;

  formatPopulation(value: unknown): string {
    return Number(value ?? 0).toLocaleString();
  }

  populationPercent(value: unknown): number {
    return Math.min(
      100,
      (Number(value ?? 0) / this.maxPopulation) * 100,
    );
  }

  readonly tableColumns: readonly WorkspaceSimpleTableColumn<DesignSystemTableRow>[] =
    [
      {
        key: 'entity',
        label: 'Entity',
        width: 'minmax(180px, 2fr)',
      },
      {
        key: 'records',
        label: 'Records',
        type: 'number',
        align: 'right',
        width: 'minmax(100px, 1fr)',
      },
      {
        key: 'errors',
        label: 'Errors',
        type: 'error-count',
        align: 'right',
        width: 'minmax(80px, 0.7fr)',
      },
      {
        key: 'warnings',
        label: 'Warnings',
        type: 'warning-count',
        align: 'right',
        width: 'minmax(90px, 0.8fr)',
      },
      {
        key: 'status',
        label: 'Status',
        type: 'status',
        width: 'minmax(110px, 1fr)',
      },
    ];

  getWideTableColumns(
    entityTemplate: TemplateRef<unknown>,
    populationTemplate: TemplateRef<unknown>,
  ): readonly WorkspaceSimpleTableColumn<DesignSystemWideTableRow>[] {
    return [
      {
        key: 'entity',
        label: 'Entity',
        width: 'minmax(210px, 2fr)',
        template: entityTemplate as WorkspaceSimpleTableColumn<DesignSystemWideTableRow>['template'],
      },
      {
        key: 'records',
        label: 'Records',
        type: 'number',
        width: '100px',
        align: 'right',
      },
      {
        key: 'errors',
        label: 'Errors',
        type: 'error-count',
        width: '80px',
        align: 'right',
      },
      {
        key: 'warnings',
        label: 'Warnings',
        type: 'warning-count',
        width: '100px',
        align: 'right',
      },
      {
        key: 'relationships',
        label: 'Relationships',
        type: 'number',
        width: '120px',
        align: 'right',
      },
      {
        key: 'population',
        label: 'Population',
        width: '170px',
        align: 'right',
        template: populationTemplate as WorkspaceSimpleTableColumn<DesignSystemWideTableRow>['template'],
      },
      {
        key: 'status',
        label: 'Status',
        type: 'status',
        width: '110px',
      },
    ];
  }

  getEntityDescription(entity: string): string {
    const descriptions: Record<string, string> = {
      Customer: 'Business partner master data',
      'Sales Order': 'Order header entity',
      'Order Item': 'Order line-level entity',
      Delivery: 'Outbound logistics document',
      'Delivery Item': 'Delivery line-level entity',
      Invoice: 'Billing document',
      'Invoice Item': 'Billing line-level entity',
      Payment: 'Financial settlement entity',
      'Credit Memo': 'Credit adjustment document',
      'Accounting Document': 'Financial accounting entity',
      'Material Document': 'Inventory movement document',
      'Purchase Order': 'Procurement document',
      'Purchase Order Item': 'Procurement line-level entity',
      'Goods Receipt': 'Inbound inventory movement',
      Material: 'Material master data',
      Plant: 'Operational plant master',
      'Storage Location': 'Inventory storage master',
      'Business Partner': 'Business partner master',
      'Company Code': 'Legal entity master',
      'Sales Organization': 'Sales organizational unit',
      'Distribution Channel': 'Distribution structure',
      Division: 'Product division',
      'Customer Group': 'Customer segmentation',
      'Material Group': 'Material classification',
      'Shipping Point': 'Shipping execution unit',
      Route: 'Transportation route',
      'Payment Terms': 'Payment condition master',
      Incoterms: 'International trade terms',
    };

    return descriptions[entity] ?? 'Model entity';
  }


  updateTableSearch(value: string): void {
    this.tableSearch.set(value);
  }

  get filteredTableRows(): readonly DesignSystemTableRow[] {
    const query = this.tableSearch().trim().toLowerCase();

    if (!query) {
      return this.tableRows;
    }

    return this.tableRows.filter((row) =>
      row.entity.toLowerCase().includes(query),
    );
  }
}
