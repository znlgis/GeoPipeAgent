import { getLocale } from '@/locales'

/**
 * Shared formatting utilities.
 */

/** Map app locale to BCP 47 locale string for Intl APIs. */
function resolveLocale(): string {
  const locale = getLocale()
  return locale === 'en-US' ? 'en-US' : 'zh-CN'
}

/**
 * Format an ISO-8601 date string respecting the current app locale.
 */
export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString(resolveLocale(), {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format a time string respecting the current app locale.
 */
export function formatTime(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleTimeString(resolveLocale(), {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}
