/**
 * Formats status identifiers for display only.
 * Keep canonical status values unchanged for application logic.
 */
export function formatStatusLabel(status: string | null | undefined): string {
  if (!status?.trim()) {
    return 'Unknown';
  }

  return status
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}
