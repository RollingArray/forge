/**
 * File: favorite.interface.ts
 * Purpose: Frontend contracts for the Favorites feature.
 */

import { ResourceType } from '../types/resource-type.type';

export interface Favorite {
  favorite_id: string;
  resource_type: ResourceType;
  data_model_id: string;
  data_model_name: string;
  job_id: string | null;
  entity_name: string | null;
  status: string | null;
  created_at: string;
}

export interface CreateFavoriteRequest {
  resource_type: ResourceType;
  data_model_id: string;
  job_id?: string;
  entity_name?: string;
}
