import { ValidationMetric } from './validation-metric.interface';

export interface ValidationRecord {
  label: string;
  details: ValidationMetric[];
}
