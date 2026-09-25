/**
 * File: data-model-access.interface.ts
 * Purpose: Frontend access contracts for FORGE Data Model collaboration.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

export type DataModelAccessRole =
  | 'OWNER'
  | 'CONTRIBUTOR'
  | 'VIEWER';

export interface DataModelAccess {
  dataModelId: string;
  userId: string;
  displayName: string;
  email: string;
  role: DataModelAccessRole;
  grantedAt: string | null;
}
