/**
 * File: update-data-model-request.interface.ts
 * Purpose: API request contract for updating a FORGE Data Model.
 */

export interface UpdateDataModelRequest {
  name: string;
  description: string;
  color: string;
  tags: string[];
}
