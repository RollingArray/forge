/**
 * File: api-loading-skip.token.ts
 * Purpose: Controls whether an HTTP request participates in global loading UI.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

import { HttpContextToken } from '@angular/common/http';

export const API_LOADING_SKIP = new HttpContextToken<boolean>(
  () => false,
);
