import { test, expect } from '@playwright/test'

test.describe('GeoPipeAgent Web UI', () => {
  test('homepage loads with pipeline editor', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('text=GeoPipeAgent')).toBeVisible()
  })

  test('navigation menu has 3 items', async ({ page }) => {
    await page.goto('/')
    const menuItems = page.locator('.el-menu-item')
    await expect(menuItems).toHaveCount(3)
  })

  test('can navigate to chat page', async ({ page }) => {
    await page.goto('/')
    await page.click('text=AI')
    await expect(page).toHaveURL(/\/chat/)
  })

  test('can navigate to history page', async ({ page }) => {
    await page.goto('/')
    await page.click('text=History')
    await expect(page).toHaveURL(/\/history/)
  })

  test('theme toggle button exists', async ({ page }) => {
    await page.goto('/')
    const themeBtn = page.locator('.theme-toggle')
    await expect(themeBtn).toBeVisible()
  })

  test('language toggle button exists', async ({ page }) => {
    await page.goto('/')
    const localeBtn = page.locator('.locale-toggle')
    await expect(localeBtn).toBeVisible()
  })
})
