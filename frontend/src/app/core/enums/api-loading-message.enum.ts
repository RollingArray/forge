/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: api-loading-message.enum.ts
 * Purpose: Defines messages displayed during FORGE API operations.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export enum ApiLoadingMessage {
  Loading = 'Loading...',
  LoadingWorkspace = 'Loading workspace...',
  CreatingDataModel = 'Creating Data Model...',
  GeneratingDataModelWithAI = 'Generating Data Model with FORGE AI...',
  GeneratingSemanticPreviewWithAI = 'Generating semantic preview with FORGE AI...',
  GeneratingFieldProposalWithAI = 'Generating field proposal with FORGE AI...',
  GeneratingIdentityProposalWithAI = 'Generating identity proposal with FORGE AI...',
  UpdatingDataModel = 'Updating Data Model...',
  DeletingDataModel = 'Deleting Data Model...',
  LoadingSpecification = 'Loading Data Model specification...',
  CreatingEntity = 'Adding entity to Data Model...',
  CreatingField = 'Adding field to Data Model...',
  UpdatingEntityIdentity = 'Updating entity identity...',
  UpdatingField = 'Updating field definition...',
}
