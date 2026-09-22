import {
  Activity,
  Metric,
  OverviewItem,
  QuickAction,
  Session,
  Template,
} from '../models/home.models';

export const HOME_METRICS: Metric[] = [
  {
    label: 'Total Sessions',
    value: '12',
    icon: 'database',
    accent: 'purple',
    supportingText: '+3 this month',
    supportingType: 'positive',
  },
  {
    label: 'Total Entities',
    value: '186',
    icon: 'account_tree',
    accent: 'purple',
    supportingText: 'Across all sessions',
    supportingType: 'subtle',
  },
  {
    label: 'Generated Datasets',
    value: '8',
    icon: 'description',
    accent: 'green',
    supportingText: '1 in progress',
    supportingType: 'progress',
  },
  {
    label: 'Total Records',
    value: '3.2M',
    icon: 'schedule',
    accent: 'purple',
    supportingText: 'Across all datasets',
    supportingType: 'subtle',
  },
];

export const HOME_SESSIONS: Session[] = [
  {
    name: 'SAP Order-to-Cash',
    description:
      'End-to-end O2C data model for SAP tables with relationships',
    entities: 21,
    relationships: 29,
    updated: 'Updated 2 hours ago',
    status: 'Modeling',
    icon: 'cube',
    accent: 'purple',
  },
  {
    name: 'MES Quality Model',
    description:
      'Manufacturing quality and inspection data generation',
    entities: 8,
    relationships: 12,
    updated: 'Updated 1 day ago',
    status: 'Validated',
    icon: 'factory',
    accent: 'green',
  },
  {
    name: 'Customer 360',
    description:
      'CRM customer and engagement data model',
    entities: 14,
    relationships: 18,
    updated: 'Updated 3 days ago',
    status: 'Draft',
    icon: 'groups',
    accent: 'blue',
  },
  {
    name: 'PLM Engineering Data',
    description:
      'Product lifecycle and engineering data model',
    entities: 26,
    relationships: 34,
    updated: 'Updated 5 days ago',
    status: 'Generated',
    icon: 'settings',
    accent: 'purple',
  },
  {
    name: 'Test Model',
    description: 'Basic model for testing',
    entities: 5,
    relationships: 4,
    updated: 'Updated 1 week ago',
    status: 'Draft',
    icon: 'description',
    accent: 'gray',
  },
  {
    name: 'Supplier Master Data',
    description:
      'Supplier, purchasing organization and material master data',
    entities: 17,
    relationships: 23,
    updated: 'Updated 1 week ago',
    status: 'Validated',
    icon: 'inventory_2',
    accent: 'green',
  },
  {
    name: 'Aircraft Parts Model',
    description:
      'Aircraft parts, assemblies and configuration data',
    entities: 19,
    relationships: 27,
    updated: 'Updated 2 weeks ago',
    status: 'Modeling',
    icon: 'precision_manufacturing',
    accent: 'blue',
  },
  {
    name: 'Maintenance Operations',
    description:
      'Maintenance events, work orders and operational history',
    entities: 13,
    relationships: 16,
    updated: 'Updated 2 weeks ago',
    status: 'Generated',
    icon: 'build_circle',
    accent: 'purple',
  },
  {
    name: 'Inventory Planning',
    description:
      'Inventory, warehouse and replenishment planning model',
    entities: 11,
    relationships: 15,
    updated: 'Updated 3 weeks ago',
    status: 'Draft',
    icon: 'warehouse',
    accent: 'gray',
  },
  {
    name: 'Supplier Quality Analytics',
    description:
      'Supplier quality, inspection and non-conformance data',
    entities: 16,
    relationships: 21,
    updated: 'Updated 1 month ago',
    status: 'Validated',
    icon: 'analytics',
    accent: 'green',
  },
];

export const HOME_TEMPLATES: Template[] = [
  {
    name: 'SAP Template',
    description:
      'Common SAP tables with standard relationships',
    icon: 'table_view',
    accent: 'blue',
  },
  {
    name: 'Manufacturing Template',
    description:
      'MES and production data model',
    icon: 'factory',
    accent: 'green',
  },
  {
    name: 'CRM Template',
    description:
      'Customer and sales data model',
    icon: 'groups',
    accent: 'purple',
  },
  {
    name: 'Blank Template',
    description:
      'Start with an empty model',
    icon: 'description',
    accent: 'gray',
  },
];

export const HOME_QUICK_ACTIONS: QuickAction[] = [
  {
    label: 'New Session',
    icon: 'add',
    action: 'new-session',
  },
  {
    label: 'Import Metadata',
    icon: 'upload',
    action: 'import-metadata',
  },
  {
    label: 'View Documentation',
    icon: 'menu_book',
    action: 'documentation',
  },
  {
    label: 'Open Settings',
    icon: 'settings',
    action: 'settings',
  },
];

export const HOME_ACTIVITIES: Activity[] = [
  {
    action: 'Generated dataset',
    session: 'SAP Order-to-Cash',
    time: '2h ago',
    icon: 'database',
    accent: 'purple',
  },
  {
    action: 'Model validated',
    session: 'MES Quality Model',
    time: '1d ago',
    icon: 'check_circle',
    accent: 'green',
  },
  {
    action: 'Added entity',
    session: 'Customer 360',
    time: '3d ago',
    icon: 'add_circle',
    accent: 'purple',
  },
  {
    action: 'Updated constraints',
    session: 'PLM Engineering Data',
    time: '5d ago',
    icon: 'tune',
    accent: 'purple',
  },
  {
    action: 'Created session',
    session: 'Test Model',
    time: '1w ago',
    icon: 'folder_open',
    accent: 'blue',
  },
  {
    action: 'Updated relationships',
    session: 'SAP Order-to-Cash',
    time: '1w ago',
    icon: 'link',
    accent: 'purple',
  },
  {
    action: 'Imported metadata',
    session: 'MES Quality Model',
    time: '1w ago',
    icon: 'upload_file',
    accent: 'green',
  },
  {
    action: 'Added entity',
    session: 'PLM Engineering Data',
    time: '2w ago',
    icon: 'add_circle',
    accent: 'purple',
  },
  {
    action: 'Model updated',
    session: 'Customer 360',
    time: '2w ago',
    icon: 'edit',
    accent: 'blue',
  },
  {
    action: 'Validation completed',
    session: 'SAP Order-to-Cash',
    time: '2w ago',
    icon: 'verified',
    accent: 'green',
  },
  {
    action: 'Added relationship',
    session: 'Test Model',
    time: '3w ago',
    icon: 'link',
    accent: 'purple',
  },
  {
    action: 'Session created',
    session: 'Customer 360',
    time: '3w ago',
    icon: 'create_new_folder',
    accent: 'blue',
  },
  {
    action: 'Updated field rules',
    session: 'MES Quality Model',
    time: '1mo ago',
    icon: 'tune',
    accent: 'green',
  },
  {
    action: 'Generated preview',
    session: 'PLM Engineering Data',
    time: '1mo ago',
    icon: 'dataset',
    accent: 'purple',
  },
];

export const HOME_OVERVIEW: OverviewItem[] = [
  {
    number: 1,
    title: 'Session Overview',
    description:
      'Quick view of recent sessions with key information (entities, relationships, status) for easy access.',
  },
  {
    number: 2,
    title: 'Templates',
    description:
      'Pre-defined templates to quickly start common enterprise data models (SAP, Manufacturing, CRM, etc.).',
  },
  {
    number: 3,
    title: 'Quick Actions',
    description:
      'Common tasks like creating a new session or importing metadata.',
  },
  {
    number: 4,
    title: 'Activity & Guidance',
    description:
      'Recent activity across sessions and quick access to help and documentation.',
  },
];
