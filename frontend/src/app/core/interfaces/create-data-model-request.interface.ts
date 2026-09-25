/**
 * File: create-data-model-request.interface.ts
 * Purpose: API request contract for creating a FORGE Data Model.
 */

export interface CreateDataModelRequest {
  name: string;
  description: string;
  color: string;
  tags: string[];
}
