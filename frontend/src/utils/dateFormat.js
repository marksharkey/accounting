/**
 * Format a date string (YYYY-MM-DD or ISO) to local date string
 * Avoids JavaScript's UTC interpretation of date strings
 *
 * @param {string} dateString - Date in format "YYYY-MM-DD" or ISO format
 * @returns {string} - Formatted date string (e.g., "4/1/2026")
 */
export function formatLocalDate(dateString) {
  if (!dateString) return '';

  // Handle ISO date format (2026-04-01 or 2026-04-01T00:00:00)
  const datePart = dateString.split('T')[0];
  const [year, month, day] = datePart.split('-').map(Number);

  // Create date in local timezone (not UTC)
  const date = new Date(year, month - 1, day);

  return date.toLocaleDateString();
}
