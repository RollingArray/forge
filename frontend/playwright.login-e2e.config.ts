import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: [
    'login/**/*.spec.ts',
    'multi-user/**/*.spec.ts',
    'real-email/**/*.spec.ts',
  ],
  fullyParallel: false,
  workers: 1,
  timeout: 7 * 60 * 1000,
  expect: {
    timeout: 20_000,
  },
  reporter: [['list']],
  outputDir: 'test-results/login-e2e',
  use: {
    baseURL: 'http://127.0.0.1:18866',
    ...devices['Desktop Chrome'],
    headless: false,
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
});
