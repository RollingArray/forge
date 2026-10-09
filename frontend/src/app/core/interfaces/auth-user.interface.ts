export interface AuthUser {
  userId: string;
  email: string;
  displayName: string;
  employeeId?: string | null;
  profile?: Record<string, unknown> | null;
}
