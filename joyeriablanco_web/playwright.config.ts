import { defineConfig, devices } from '@playwright/test'

/**
 * E2E contra la API aislada `api-e2e` (docker compose --profile e2e), con su propia BD.
 * Vite se levanta en el puerto 5174 con proxy de /api a http://localhost:8001 (research R-16).
 */
const E2E_PORT = 5174

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  globalSetup: './e2e/global-setup.ts',
  use: {
    baseURL: `http://localhost:${E2E_PORT}`,
    locale: 'es-ES',
    timezoneId: 'Europe/Madrid',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npx vite --port ${E2E_PORT}`,
    url: `http://localhost:${E2E_PORT}`,
    reuseExistingServer: !process.env.CI,
    env: { VITE_API_PROXY: 'http://localhost:8001', VITE_PORT: String(E2E_PORT) },
    timeout: 60_000,
  },
})
