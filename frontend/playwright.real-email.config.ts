import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/real-email',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  workers: 1,
  timeout: 7 * 60 * 1000,
  expect: {
    timeout: 20_000,
  },
  reporter: [['list']],
  outputDir: 'test-results/real-email',
  use: {
    baseURL: 'http://127.0.0.1:18866',
    ...devices['Desktop Chrome'],
    headless: false,
    launchOptions: {
      slowMo: 150,
    },
    storageState: {
      cookies: [],
      origins: [],
    },
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
});
