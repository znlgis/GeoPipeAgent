/**
 * Shared formatting utilities.
 */

/**
 * Format an ISO-8601 date string for Chinese locale display.
 */
export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
