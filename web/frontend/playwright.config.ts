import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for GeoPipeAgent Web UI E2E tests.
 *
 * Prerequisites:
 *   1. Start the backend: uvicorn web.backend.main:app --host 0.0.0.0 --port 8000
 *   2. Start the frontend: cd web/frontend && npm run dev
 *   3. Install browsers: npx playwright install
 *   4. Run tests: npx playwright test
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'cd ../.. && uvicorn web.backend.main:app --host 0.0.0.0 --port 8000',
      url: 'http://localhost:8000/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
})
