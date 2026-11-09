import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/login',
  testMatch: ['login.spec.ts', 'login-verification.spec.ts'],
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  reporter: [['list']],
  outputDir: 'test-results/login-ui',
  use: {
    baseURL: 'http://127.0.0.1:18866',
    ...devices['Desktop Chrome'],
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
