export type Accent =
  | 'purple'
  | 'green'
  | 'blue'
  | 'gray'
  | 'orange';

export type SessionStatus =
  | 'Modeling'
  | 'Validated'
  | 'Draft'
  | 'Generated';

export interface Session {
  name: string;
  description: string;
  entities: number;
  relationships: number;
  updated: string;
  status: SessionStatus;
  icon: string;
  accent: Accent;
}

export interface Template {
  name: string;
  description: string;
  icon: string;
  accent: Accent;
}

export interface Activity {
  action: string;
  session: string;
  time: string;
  icon: string;
  accent: Accent;
}

export interface Metric {
  label: string;
  value: string;
  icon: string;
  accent: Accent;
  supportingText: string;
  supportingType: 'positive' | 'subtle' | 'progress';
}

export interface QuickAction {
  label: string;
  icon: string;
  action: string;
}

export interface OverviewItem {
  number: number;
  title: string;
  description: string;
}
