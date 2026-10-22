import { QualityEvidenceItem } from './quality-evidence-item.interface';

export interface QualityEvidenceSection {
  key: string;
  title: string;
  description: string;
  items: QualityEvidenceItem[];
}
