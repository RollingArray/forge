import { CheckStatus } from '../types/check-status.type';
import { ValidationMetric } from './validation-metric.interface';
import { ValidationRecord } from './validation-record.interface';

export interface ValidationCheck {
  key: string;
  title: string;
  description: string;
  status: CheckStatus;
  statusLabel: string;
  issueCount: number | null;
  metrics: ValidationMetric[];
  records: ValidationRecord[];
}
