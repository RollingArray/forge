/**
 * File: data-model-response.interface.ts
 * Purpose: API response contract for FORGE Data Models.
 */

export interface DataModelResponse {
  data_model_id: string;
  owner_user_id: string;
  name: string;
  description: string;
  color: string;
  tags: string[];
  status: string;
  created_at: string;
  updated_at: string;
}
