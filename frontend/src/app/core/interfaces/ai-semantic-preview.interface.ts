/**
 * File: ai-semantic-preview.interface.ts
 * Purpose: Defines the frontend contract for FORGE semantic generation previews.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

export type AISemanticPreviewStatus =
  | 'PROPOSE'
  | 'CLARIFY'
  | 'UNSUPPORTED';

export interface AISemanticPreview {
  status: AISemanticPreviewStatus;
  message: string;
  previewValues: string[];
}
