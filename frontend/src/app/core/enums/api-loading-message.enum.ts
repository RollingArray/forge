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
  LoadingWorkspace = 'Loading workspace...',
  CreatingDataModel = 'Creating Data Model...',
  GeneratingDataModelWithAI = 'Generating Data Model with FORGE AI...',
  GeneratingSemanticPreviewWithAI = 'Generating semantic preview with FORGE AI...',
  GeneratingFieldProposalWithAI = 'Generating field proposal with FORGE AI...',
  GeneratingIdentityProposalWithAI = 'Generating identity proposal with FORGE AI...',
  GeneratingRelationshipProposalWithAI = 'Generating relationship proposal with FORGE AI...',
  GeneratingForeignKeyProposalWithAI = 'Generating foreign key proposal with FORGE AI...',
  GeneratingConstraintProposalWithAI = 'Generating constraint proposal with FORGE AI...',
  UpdatingDataModel = 'Updating Data Model...',
  DeletingDataModel = 'Deleting Data Model...',
  LoadingDataModel = 'Loading Data Model...',
  LoadingDataModels = 'Loading Data Models...',
  LoadingPopulationPlan = 'Loading population plan...',
  BuildingCandidatePopulationPlan = 'Building candidate population plan...',
  SavingPopulationPlan = 'Saving population plan...',
  DownloadingGeneratedFile = 'Downloading generated file...',
  GrantingDataModelAccess = 'Granting data model access...',
  LoadingDataModelAccess = 'Loading data model access...',
  UpdatingDataModelAccess = 'Updating data model access...',
  RevokingDataModelAccess = 'Revoking data model access...',

  LoadingGenerationReadiness = 'Loading generation readiness...',
  CreatingGenerationJob = 'Creating generation job...',
  StartingGeneration = 'Starting generation...',
  LoadingGenerationJob = 'Loading generation job...',
  LoadingGenerationCheckpoint = 'Loading generation checkpoint...',
  LoadingGeneratedFiles = 'Loading generated files...',
  LoadingArtifactPreview = 'Loading artifact preview...',
  LoadingSpecification = 'Loading Data Model specification...',
  CreatingEntity = 'Adding entity to Data Model...',
  CreatingField = 'Adding field to Data Model...',
  CreatingRelationship = 'Adding relationship to Data Model...',
  UpdatingRelationship = 'Updating relationship...',
  DeletingRelationship = 'Removing relationship from Data Model...',
  CreatingConstraint = 'Adding constraint to Data Model...',
  UpdatingConstraint = 'Updating constraint...',
  DeletingConstraint = 'Removing constraint from Data Model...',
  UpdatingEntityIdentity = 'Updating entity identity...',
  UpdatingField = 'Updating field definition...',
  CreatingForeignKey = 'Adding foreign key to Data Model...',
  UpdatingForeignKey = 'Updating foreign key...',
  DeletingForeignKey = 'Removing foreign key from Data Model...',
}
