import { describe, it, expect } from 'vitest'
import zhCN from './zh-CN'
import enUS from './en-US'

describe('locale files', () => {
  it('zh-CN and en-US have the same top-level keys', () => {
    const zhKeys = Object.keys(zhCN).sort()
    const enKeys = Object.keys(enUS).sort()
    expect(zhKeys).toEqual(enKeys)
  })

  it('zh-CN and en-US have the same nested keys', () => {
    for (const section of Object.keys(zhCN) as (keyof typeof zhCN)[]) {
      const zhKeys = Object.keys(zhCN[section]).sort()
      const enKeys = Object.keys(enUS[section]).sort()
      expect(zhKeys).toEqual(enKeys)
    }
  })

  it('no empty string values in zh-CN', () => {
    for (const section of Object.values(zhCN)) {
      for (const [key, value] of Object.entries(section)) {
        expect(value, `zh-CN: ${key}`).not.toBe('')
      }
    }
  })

  it('no empty string values in en-US', () => {
    for (const section of Object.values(enUS)) {
      for (const [key, value] of Object.entries(section)) {
        expect(value, `en-US: ${key}`).not.toBe('')
      }
    }
  })
})
