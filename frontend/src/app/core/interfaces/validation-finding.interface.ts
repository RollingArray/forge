export interface ValidationFinding {
  id: number;
  severity: 'error' | 'warning';
  title: string;
  details: string;
  category: string;
}
