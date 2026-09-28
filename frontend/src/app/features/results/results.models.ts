export interface GenerationArtifact {
  entity_name: string;
  filename: string;
  rows: number;
  size_bytes: number;
}

export interface GenerationArtifactPreview {
  entity_name: string;
  filename: string;
  columns: string[];
  rows: Record<string, string | null>[];
  total_rows: number;
  preview_rows: number;
}
