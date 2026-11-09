import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/multi-user',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: {
    timeout: 20_000,
  },
  reporter: [['list']],
  outputDir: 'test-results/multi-user',
  use: {
    baseURL: 'http://127.0.0.1:18866',
    ...devices['Desktop Chrome'],
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
