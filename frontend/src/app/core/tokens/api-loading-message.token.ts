/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: api-loading-message.token.ts
 * Purpose: Defines the HTTP context token used to provide API loading messages.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import { HttpContextToken } from '@angular/common/http';

import { ApiLoadingMessage } from '../enums/api-loading-message.enum';

export const API_LOADING_MESSAGE = new HttpContextToken<ApiLoadingMessage>(
  () => ApiLoadingMessage.Loading,
);
