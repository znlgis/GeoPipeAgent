import { describe, it, expect } from 'vitest'
import { formatDate } from './format'

describe('formatDate', () => {
  it('formats an ISO date string', () => {
    const result = formatDate('2026-03-29T10:30:00.000Z')
    // Should contain year, month, day
    expect(result).toContain('2026')
    expect(result).toContain('03')
    expect(result).toContain('29')
  })

  it('handles date-only strings', () => {
    const result = formatDate('2026-01-15')
    expect(result).toContain('2026')
    expect(result).toContain('01')
    expect(result).toContain('15')
  })
})
