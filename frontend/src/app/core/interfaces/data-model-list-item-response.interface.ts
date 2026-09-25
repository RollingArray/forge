// FORGE — Framework for Observed Rules, Generation & Engineered Data

export interface DataModelListItemResponse {
  data_model_id: string;
  owner_user_id: string;
  name: string;
  description: string;
  color: string;
  tags: string[];
  status: string;
  created_at: string;
  updated_at: string;
  access_role: 'OWNER' | 'CONTRIBUTOR' | 'VIEWER';
}
