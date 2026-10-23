// @ts-check
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  retries: 1,
  use: {
    headless: true,
    userAgent: 'Mozilla/5.0 (compatible; DiomikaE2E/1.0)',
  },
  reporter: 'list',
})
