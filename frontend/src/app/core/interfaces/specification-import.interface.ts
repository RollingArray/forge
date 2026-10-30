/**
 * API contracts for the incremental CSV Specification Wizard.
 */

export interface SpecificationImportCsv {
  entities: string;
  fields_and_keys: string;
  foreign_keys: string;
  relationships: string;
  constraints: string;
}

export interface SpecificationImportApplyRequest {
  base_revision: string;
  csv_digest: string;
  csv: SpecificationImportCsv;
}

export interface SpecificationImportPreviewResponse {
  base_revision: string;
  csv_digest: string;
  can_apply: boolean;
  summary: Record<string, number>;
  sections: Record<string, unknown>;
  additions: Record<string, unknown>[];
  already_present: Record<string, unknown>[];
  conflicts: Record<string, unknown>[];
  issues: Record<string, unknown>[];
}

export interface SpecificationImportApplyResponse {
  applied: boolean;
  summary: Record<string, number>;
  specification_revision: string;
}
