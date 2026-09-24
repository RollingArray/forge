/**
 * File: auth-user.interface.ts
 * Purpose: Authenticated FORGE user contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

export interface AuthUser {
  userId: string;
  email: string;
  displayName: string;
}
